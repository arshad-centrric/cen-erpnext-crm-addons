import frappe
import json
from frappe.utils import cint, flt
from cen_crm_addons.api.sales_order_hooks import make_quotation_wrapper as make_quotation


@frappe.whitelist()
def create_quotation(opportunity_id, items=None, submit=0):
    """
    Create a Quotation from an Opportunity.
    opportunity_id: The ID of the Opportunity (Required)
    items: JSON string or list of dicts containing item_code, qty, rate (Optional. If provided, overrides the items from Opportunity)
    submit: 1 to submit immediately, 0 to leave as Draft
    """
    if not opportunity_id:
        frappe.throw("Opportunity ID is a required parameter")

    if not frappe.db.exists("Opportunity", opportunity_id):
        frappe.throw(f"Opportunity {opportunity_id} not found")

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("Invalid JSON format for items payload")

    try:
        # Create mapped Quotation document from Opportunity
        # This copies over customer, company, taxes, and items automatically
        quotation_doc = make_quotation(opportunity_id)
        
        # If the mobile app provides specific items/prices, replace the default ones
        if items and isinstance(items, list):
            quotation_doc.set("items", [])  # Clear default mapped items
            
            for item in items:
                if not item.get("item_code") or not item.get("qty"):
                    frappe.throw("Each item must contain at least an 'item_code' and 'qty'")
                    
                new_rate = flt(item.get("rate")) if item.get("rate") else 0.0
                row_data = {
                    "item_code": str(item.get("item_code")).strip(),
                    "qty": flt(item.get("qty")),
                    "rate": new_rate,
                    "price_list_rate": new_rate,
                    "discount_percentage": 0.0,
                    "discount_amount": 0.0,
                    "margin_type": "",
                    "margin_rate_or_amount": 0.0
                }
                
                if item.get("uom"):
                    row_data["uom"] = str(item.get("uom")).strip()
                    
                quotation_doc.append("items", row_data)
        else:
            # If items were mapped from Opportunity, they lack price_list_rate which breaks calculations
            for row in quotation_doc.get("items"):
                row.price_list_rate = row.rate
                row.discount_percentage = 0.0
                row.discount_amount = 0.0
                row.margin_rate_or_amount = 0.0

        # Unconditionally recalculate totals to simulate frontend behavior
        quotation_doc.run_method("set_missing_values")
        quotation_doc.run_method("calculate_taxes_and_totals")
        
        # Defensive fallback: If items had 0 rate, calculations might skip and leave totals as None
        for field in ["grand_total", "base_grand_total", "net_total", "base_net_total", "rounded_total", "base_rounded_total", "total_taxes_and_charges", "base_total_taxes_and_charges"]:
            if getattr(quotation_doc, field, None) is None:
                setattr(quotation_doc, field, 0.0)

        # Insert the document (creates it as a Draft)
        quotation_doc.insert()

        # Submit if requested
        if cint(submit) == 1:
            quotation_doc.submit()

        return {
            "status": "success",
            "message": f"Quotation {quotation_doc.name} has been created.",
            "data": {
                "name": quotation_doc.name,
                "docstatus": quotation_doc.docstatus,
                "grand_total": quotation_doc.grand_total,
                "status": quotation_doc.status
            }
        }
    except Exception as e:
        frappe.log_error(title="Quotation Creation API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to create Quotation: {e!s}")


@frappe.whitelist()
def get_quotation_details(quotation_id):
    """
    Fetch all details of a specific Quotation including its items and custom fields.
    """
    if not quotation_id:
        frappe.throw("Quotation ID is required")

    try:
        doc = frappe.get_doc("Quotation", quotation_id)
        doc_dict = doc.as_dict()

        # Fetch linked Sales Orders and their status
        linked_sales_orders = frappe.db.sql("""
            SELECT DISTINCT so.name, so.status, so.docstatus
            FROM `tabSales Order` so
            INNER JOIN `tabSales Order Item` soi ON so.name = soi.parent
            WHERE soi.prevdoc_docname = %s
        """, (quotation_id,), as_dict=True)

        doc_dict["linked_sales_orders"] = linked_sales_orders

        return {
            "status": "success",
            "data": doc_dict
        }
    except frappe.DoesNotExistError:
        frappe.throw(f"Quotation {quotation_id} not found")
    except Exception as e:
        frappe.log_error(title="Fetch Quotation Details API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to fetch details: {e!s}")


@frappe.whitelist()
def update_quotation_items(quotation_id, items):
    """
    Update the items table of a Quotation (Draft or Submitted).
    This performs a PARTIAL update. Any items not mentioned in the payload will be kept unchanged.
    items: JSON string or list of dicts. 
           Should contain 'name' (child row ID) to update an existing row.
    """
    from erpnext.controllers.accounts_controller import update_child_qty_rate
    
    if not quotation_id or not items:
        frappe.throw("Quotation ID and Items are required")

    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("Invalid JSON format for items payload")

    try:
        doc = frappe.get_doc("Quotation", quotation_id)
        
        if doc.docstatus == 2:
            frappe.throw("Cannot update a Cancelled Quotation.")

        # Create a lookup for the updates provided by the mobile app
        updates_by_name = {str(item.get("name")).strip(): item for item in items if item.get("name")}
        new_items = [item for item in items if not item.get("name")]

        existing_names = [row.name for row in doc.items]
        for update_name in updates_by_name.keys():
            if update_name not in existing_names:
                frappe.throw(f"Item Row ID '{update_name}' does not exist in this Quotation. Please check the 'name' field.")

        if doc.docstatus == 1:
            # For submitted quotations, we MUST pass the FULL list of items to update_child_qty_rate,
            # otherwise it will delete the ones we don't pass.
            if new_items:
                frappe.throw("Cannot add new items to a Submitted Quotation. You can only update existing rows by providing their 'name'.")
                
            trans_items = []
            for existing_row in doc.items:
                # If the mobile app sent an update for this row, use it. Otherwise, keep existing values.
                if existing_row.name in updates_by_name:
                    update_data = updates_by_name[existing_row.name]
                    new_rate = flt(update_data.get("rate")) if update_data.get("rate") is not None else flt(existing_row.rate)
                    
                    trans_items.append({
                        "docname": existing_row.name,
                        "item_code": existing_row.item_code,
                        "qty": flt(update_data.get("qty")),
                        "rate": new_rate
                    })
                    
                    # Fix for ERPNext core quirk: update_child_qty_rate doesn't recalculate discounts for Quotation!
                    # So we must update price_list_rate in the DB so that calculate_taxes_and_totals respects the new rate
                    # We also must clear margins to prevent the margin from being added on top of our new rate.
                    frappe.db.set_value("Quotation Item", existing_row.name, {
                        "price_list_rate": new_rate,
                        "discount_percentage": 0.0,
                        "discount_amount": 0.0,
                        "margin_type": "",
                        "margin_rate_or_amount": 0.0
                    })
                else:
                    trans_items.append({
                        "docname": existing_row.name,
                        "item_code": existing_row.item_code,
                        "qty": flt(existing_row.qty),
                        "rate": flt(existing_row.rate)
                    })

            update_child_qty_rate(
                parent_doctype="Quotation",
                parent_doctype_name=quotation_id,
                child_docname="items",
                trans_items=json.dumps(trans_items)
            )
            
            # Reload to get updated totals
            doc.reload()
            
            return {
                "status": "success",
                "message": f"Submitted Quotation {quotation_id} items updated successfully.",
                "data": {
                    "name": doc.name,
                    "grand_total": doc.grand_total,
                    "net_total": doc.net_total
                }
            }

        else:
            # For Draft quotations, update existing rows in place and append new ones
            for existing_row in doc.items:
                if existing_row.name in updates_by_name:
                    update_data = updates_by_name[existing_row.name]
                    existing_row.qty = flt(update_data.get("qty"))
                    if update_data.get("rate") is not None:
                        new_rate = flt(update_data.get("rate"))
                        existing_row.rate = new_rate
                        # Also override price_list_rate to prevent recalculation from reverting the rate
                        existing_row.price_list_rate = new_rate
                        existing_row.discount_percentage = 0.0
                        existing_row.discount_amount = 0.0
                        existing_row.margin_type = ""
                        existing_row.margin_rate_or_amount = 0.0
                        
                    if update_data.get("uom"):
                        existing_row.uom = str(update_data.get("uom")).strip()

            # Append new items if any
            for new_item in new_items:
                if not new_item.get("item_code") or not new_item.get("qty"):
                    frappe.throw("Each new item must contain at least an 'item_code' and 'qty'")
                    
                new_rate = flt(new_item.get("rate")) if new_item.get("rate") is not None else 0.0
                row_data = {
                    "item_code": str(new_item.get("item_code")).strip(),
                    "qty": flt(new_item.get("qty")),
                    "rate": new_rate,
                    "price_list_rate": new_rate,
                    "discount_percentage": 0.0,
                    "discount_amount": 0.0,
                    "margin_type": "",
                    "margin_rate_or_amount": 0.0
                }
                if new_item.get("uom"):
                    row_data["uom"] = str(new_item.get("uom")).strip()

                doc.append("items", row_data)

            doc.run_method("set_missing_values")
            doc.run_method("calculate_taxes_and_totals")
            doc.save()

            return {
                "status": "success",
                "message": f"Draft Quotation {quotation_id} items updated successfully.",
                "data": {
                    "name": doc.name,
                    "grand_total": doc.grand_total,
                    "net_total": doc.net_total
                }
            }
            
    except Exception as e:
        frappe.log_error(title="Update Quotation Items API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to update quotation items: {e!s}")


@frappe.whitelist()
def cancel_quotation(quotation_id):
    """
    Cancel a Submitted Quotation.
    Automatically fetches and cancels any downstream linked documents (like Sales Orders) first.
    """
    if not quotation_id:
        frappe.throw("Quotation ID is a required parameter")

    try:
        if not frappe.db.exists("Quotation", quotation_id):
            frappe.throw(f"Quotation {quotation_id} not found")

        doc = frappe.get_doc("Quotation", quotation_id)

        if doc.docstatus == 0:
            frappe.throw(f"Quotation {quotation_id} is a Draft and cannot be cancelled. You can only delete drafts.")
            
        if doc.docstatus == 2:
            return {
                "status": "success",
                "message": f"Quotation {quotation_id} is already cancelled."
            }

        from frappe.desk.form.linked_with import get_submitted_linked_docs, cancel_all_linked_docs
        import json
        
        # Use ERPNext native logic to find and cancel all downstream documents automatically
        linked_docs_info = get_submitted_linked_docs("Quotation", quotation_id)
        linked_docs = linked_docs_info.get("docs", [])
        
        if linked_docs:
            cancel_all_linked_docs(json.dumps(linked_docs))
            # Cancelling downstream docs updates the Quotation's status/modified timestamp in the DB. 
            # We MUST reload the doc in memory before cancelling it to avoid TimestampMismatchError.
            doc.reload()

        # Cancel the Quotation
        doc.cancel()

        return {
            "status": "success",
            "message": f"Quotation {quotation_id} has been cancelled successfully."
        }

    except frappe.exceptions.LinkExistsError:
        frappe.log_error(title="Quotation Cancellation API Error", message=frappe.get_traceback())
        frappe.throw(
            f"Cannot cancel Quotation {quotation_id} because it is linked to active Sales Orders. "
            "Pass 'cancel_linked_orders': 1 in your API payload to cancel them automatically."
        )
    except Exception as e:
        frappe.log_error(title="Quotation Cancellation API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to cancel Quotation: {e!s}")
