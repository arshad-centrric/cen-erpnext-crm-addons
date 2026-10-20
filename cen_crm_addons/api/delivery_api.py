import frappe
from frappe import _
from cen_crm_addons.api.payable_amount import get_payable_amount, get_pending_amount, get_invoice_pending_amount
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

@frappe.whitelist()
def get_order_info(order_id):
    """Fetches key details for the Sales Order to display on the dashboard."""
    if not frappe.db.exists("Sales Order", order_id):
        return {"error": True, "message": "Order not found"}

    so = frappe.get_doc("Sales Order", order_id)
    
    if so.custom_picking_status != "Packed":
        frappe.throw(f"This Sales Order has not been packed yet. Current Status: {so.custom_picking_status or 'Pending'}")
    
    # Get Customer Details
    customer = frappe.get_doc("Customer", so.customer)
    
    # Check for contact info safely
    contact_mobile = so.contact_mobile or customer.get("mobile_no") or customer.get("phone")
    contact_phone = so.contact_phone or customer.get("phone") or customer.get("customer_primary_phone")
    
    # Check for linked active Sales Invoices
    linked_invoices = frappe.db.sql("""
        SELECT DISTINCT si.name, si.grand_total, si.rounded_total, si.outstanding_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus = 1
    """, (order_id,), as_dict=True)
    
    if linked_invoices:
        total_amount = sum(get_payable_amount(inv) for inv in linked_invoices)
        outstanding_amount = sum(get_invoice_pending_amount(inv) for inv in linked_invoices)
        paid_amount = total_amount - outstanding_amount
    else:
        total_amount = get_payable_amount(so)
        paid_amount = so.advance_paid
        outstanding_amount = get_pending_amount(so, paid_amount)
        
    return {
        "name": so.name,
        "customer": so.customer,
        "customer_name": so.customer_name,
        "contact_mobile": contact_mobile,
        "contact_phone": contact_phone,
        "grand_total": so.grand_total,
        "advance_paid": so.advance_paid,
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "outstanding_amount": outstanding_amount,
        "currency": so.currency,
        "status": so.status,
        "delivery_status": so.delivery_status
    }

@frappe.whitelist()
def confirm_delivery(order_id):
    """Creates and submits a Delivery Note from the Sales Order."""
    if not frappe.db.exists("Sales Order", order_id):
        frappe.throw(_("Sales Order {0} does not exist.").format(order_id))

    so = frappe.get_doc("Sales Order", order_id)

    # 1. Double check payment status (Safety Check)
    outstanding = get_pending_amount(so, so.advance_paid)
    if outstanding > 0:
        frappe.throw(_("Cannot complete delivery. This order still has an outstanding balance of {0} {1}.").format(
            outstanding, so.currency
        ))

    # 2. Check if already delivered
    if so.delivery_status == "Fully Delivered":
        frappe.throw(_("This order has already been fully delivered."))

    # 3. Create Delivery Note using standard ERPNext mapper
    dn = make_delivery_note(order_id)
    
    # 4. Save and Submit
    dn.insert()
    dn.submit()
    
    # 5. Success
    return {"name": dn.name}
