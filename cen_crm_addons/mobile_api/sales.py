import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_order_details(sales_order):
    """
    Fetch full details of a specific Sales Order for the packing app,
    including the calculated pending amount.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required")
        
    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} not found", frappe.DoesNotExistError)
        
    doc = frappe.get_doc("Sales Order", sales_order)
    
    # Convert document to dictionary
    order_details = doc.as_dict()
    
    # Dynamic outstanding calculation: check if there is an active Sales Invoice
    active_si = frappe.db.sql("""
        SELECT si.name, si.outstanding_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus = 1
        LIMIT 1
    """, (sales_order,), as_dict=True)
    
    if active_si:
        outstanding = flt(active_si[0].outstanding_amount)
        has_active_invoice = 1
        order_details["active_invoice"] = active_si[0].name
    else:
        grand_total = flt(order_details.get("grand_total", 0.0))
        advance_amount = flt(order_details.get("advance_paid", order_details.get("advance_amount", 0.0)))
        outstanding = grand_total - advance_amount
        has_active_invoice = 0
        order_details["active_invoice"] = None
        
    order_details["pending_amount"] = outstanding
    order_details["outstanding_amount"] = outstanding
    order_details["has_active_invoice"] = has_active_invoice
    
    # Fetch all non-cancelled linked Sales Invoices
    linked_sales_invoices = frappe.db.sql("""
        SELECT DISTINCT si.name, si.docstatus, si.status
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus != 2
    """, (sales_order,), as_dict=True)
    
    order_details["linked_sales_invoices"] = linked_sales_invoices
    
    return order_details


@frappe.whitelist()
def cancel_sales_order(sales_order_id):
    """
    Cancel one or multiple Submitted Sales Orders.
    `sales_order_id` can be a single string OR a JSON-encoded array of strings.
    Automatically fetches and cancels any downstream linked documents first.
    Auto-reopens "Closed" Sales Orders to allow cancellation.
    """
    import json
    if not sales_order_id:
        frappe.throw("Sales Order ID is a required parameter")

    # Parse if it's a JSON array string from the frontend
    if isinstance(sales_order_id, str) and sales_order_id.startswith("["):
        try:
            so_list = json.loads(sales_order_id)
        except Exception:
            so_list = [sales_order_id]
    elif isinstance(sales_order_id, list):
        so_list = sales_order_id
    else:
        so_list = [sales_order_id]

    results = []
    from frappe.desk.form.linked_with import get_submitted_linked_docs, cancel_all_linked_docs

    for so_id in so_list:
        try:
            if not frappe.db.exists("Sales Order", so_id):
                results.append({"sales_order": so_id, "status": "failed", "message": "Not found"})
                continue

            doc = frappe.get_doc("Sales Order", so_id)

            if doc.docstatus == 0:
                results.append({"sales_order": so_id, "status": "failed", "message": "Draft cannot be cancelled"})
                continue
                
            if doc.docstatus == 2:
                results.append({"sales_order": so_id, "status": "success", "message": "Already cancelled"})
                continue
            
            # --- NEW LOGIC: Handle "Closed" Sales Orders ---
            # ERPNext explicitly blocks cancelling a Sales Order if its status is "Closed".
            # We silently lift the lock by reverting the status before proceeding.
            if getattr(doc, "status", None) == "Closed":
                doc.db_set("status", "Draft")
                doc.reload()
            # -----------------------------------------------

            # Use ERPNext native logic to find and cancel all downstream documents automatically
            linked_docs_info = get_submitted_linked_docs("Sales Order", so_id)
            linked_docs = linked_docs_info.get("docs", [])
            
            if linked_docs:
                cancel_all_linked_docs(json.dumps(linked_docs))
                # Cancelling downstream docs updates the SO's status/modified timestamp in the DB. 
                # We MUST reload the doc in memory before cancelling it to avoid TimestampMismatchError.
                doc.reload()

            # Cancel the Sales Order
            doc.cancel()
            results.append({"sales_order": so_id, "status": "success", "message": "Cancelled successfully"})

        except Exception as e:
            frappe.log_error(title=f"Sales Order Cancellation Error for {so_id}", message=frappe.get_traceback())
            results.append({"sales_order": so_id, "status": "failed", "message": str(e)})

    return {
        "status": "success",
        "data": results
    }


@frappe.whitelist()
def get_sales_invoice_details(sales_invoice_id):
    """
    Fetch full details of a specific Sales Invoice.
    """
    if not sales_invoice_id:
        frappe.throw("Sales Invoice ID is required")
        
    if not frappe.db.exists("Sales Invoice", sales_invoice_id):
        frappe.throw(f"Sales Invoice {sales_invoice_id} not found", frappe.DoesNotExistError)
        
    doc = frappe.get_doc("Sales Invoice", sales_invoice_id)
    return doc.as_dict()

@frappe.whitelist()
def update_sales_order_items(sales_order_id, items):
    """
    Update the items of a submitted Sales Order, like the "Update Items" button in ERPNext.
    items: JSON string or list of dicts with the FULL final list of items.
           Existing rows must include 'name' (child row ID). Rows without 'name' are added.
           Existing rows left out of the list are deleted.
           Keys per row: item_code, qty, rate, uom, conversion_factor, delivery_date, description
    """
    import json
    from erpnext.controllers.accounts_controller import update_child_qty_rate
    from cen_crm_addons.api.payment_logic import sync_payment_status

    if not sales_order_id or not items:
        frappe.throw("Sales Order ID and Items are required")

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("Invalid JSON format for items payload")

    if not isinstance(items, list):
        frappe.throw("Items must be a list")

    if not frappe.db.exists("Sales Order", sales_order_id):
        frappe.throw(f"Sales Order {sales_order_id} not found", frappe.DoesNotExistError)

    try:
        doc = frappe.get_doc("Sales Order", sales_order_id)

        # Same conditions under which ERPNext shows the "Update Items" button
        if doc.docstatus != 1:
            frappe.throw(f"Sales Order {sales_order_id} must be submitted to update items")
        if doc.status in ("Closed", "Completed"):
            frappe.throw(f"Cannot update items of a {doc.status} Sales Order")
        if flt(doc.per_delivered) >= 100 or flt(doc.per_billed) >= 100:
            frappe.throw("Cannot update items of a fully delivered or fully billed Sales Order")

        if doc.get("custom_picking_status") == "Packed":
            frappe.throw("Cannot update items of a Sales Order that is already Packed")

        existing_rows = {row.name: row for row in doc.items}
        trans_items = []

        for idx, item in enumerate(items, start=1):
            row_name = str(item.get("name")).strip() if item.get("name") else None

            if row_name:
                row = existing_rows.get(row_name)
                if not row:
                    frappe.throw(f"Row #{idx}: Item Row ID '{row_name}' does not exist in this Sales Order. Please check the 'name' field.")

                if item.get("item_code") and str(item.get("item_code")).strip() != row.item_code:
                    frappe.throw(f"Row #{idx}: Item Code of an existing row cannot be changed. Remove the row and add {item.get('item_code')} as a new row.")

                # Keys left out keep their current values; ERPNext would otherwise blank them
                trans_items.append({
                    "idx": idx,
                    "docname": row.name,
                    "item_code": row.item_code,
                    "qty": flt(item.get("qty")) if item.get("qty") is not None else flt(row.qty),
                    "rate": flt(item.get("rate")) if item.get("rate") is not None else flt(row.rate),
                    "uom": str(item.get("uom")).strip() if item.get("uom") else row.uom,
                    "conversion_factor": flt(item.get("conversion_factor")) if item.get("conversion_factor") else flt(row.conversion_factor),
                    "delivery_date": item.get("delivery_date") or row.delivery_date,
                    "description": item.get("description") if item.get("description") is not None else row.description
                })
            else:
                if not item.get("item_code") or not item.get("qty"):
                    frappe.throw(f"Row #{idx}: Each new item must contain at least an 'item_code' and 'qty'")

                item_code = str(item.get("item_code")).strip()
                description = item.get("description") or frappe.db.get_value("Item", item_code, "description") or item_code

                new_row = {
                    "idx": idx,
                    "item_code": item_code,
                    "qty": flt(item.get("qty")),
                    "rate": flt(item.get("rate")) if item.get("rate") is not None else 0.0,
                    "description": description
                }
                if item.get("uom"):
                    new_row["uom"] = str(item.get("uom")).strip()
                if item.get("conversion_factor"):
                    new_row["conversion_factor"] = flt(item.get("conversion_factor"))
                if item.get("delivery_date"):
                    new_row["delivery_date"] = item.get("delivery_date")

                trans_items.append(new_row)

        if not trans_items:
            frappe.throw("A Sales Order must have at least one item")

        update_child_qty_rate(
            parent_doctype="Sales Order",
            trans_items=json.dumps(trans_items, default=str),
            parent_doctype_name=sales_order_id,
            child_docname="items"
        )

        # The app's Payment Status is not recalculated on updates after submit
        sync_payment_status(sales_order_id)

        doc.reload()

        return {
            "status": "success",
            "message": f"Sales Order {sales_order_id} items updated successfully.",
            "data": {
                "name": doc.name,
                "grand_total": doc.grand_total,
                "net_total": doc.net_total,
                "total_taxes_and_charges": doc.total_taxes_and_charges,
                "custom_payment_status": doc.get("custom_payment_status"),
                "items": [
                    {
                        "name": row.name,
                        "item_code": row.item_code,
                        "qty": row.qty,
                        "rate": row.rate,
                        "amount": row.amount,
                        "uom": row.uom,
                        "delivery_date": row.delivery_date
                    }
                    for row in doc.items
                ]
            }
        }

    except Exception as e:
        frappe.log_error(title="Update Sales Order Items API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to update sales order items: {e!s}")
