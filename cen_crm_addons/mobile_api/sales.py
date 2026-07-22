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
    
    # In standard ERPNext, the advance amount field is usually called 'advance_paid'.
    # I have added a fallback to .get("advance_amount", 0) just in case you 
    # created a custom field specifically named 'advance_amount'.
    grand_total = flt(order_details.get("grand_total", 0.0))
    advance_amount = flt(order_details.get("advance_paid", order_details.get("advance_amount", 0.0)))
    
    # Calculate and inject the pending amount
    order_details["pending_amount"] = grand_total - advance_amount
    
    return order_details