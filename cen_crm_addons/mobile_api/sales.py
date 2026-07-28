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
    
    return order_details