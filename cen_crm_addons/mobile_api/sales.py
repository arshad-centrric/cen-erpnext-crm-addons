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