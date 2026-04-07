import frappe
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

@frappe.whitelist()
def get_order_info(order_id):
    """Fetches key details for the Sales Order to display on the dashboard."""
    if not frappe.db.exists("Sales Order", order_id):
        return {"error": True}

    so = frappe.get_doc("Sales Order", order_id)
    
    # Get Customer Details
    customer = frappe.get_doc("Customer", so.customer)
    
    # Check for contact info
    contact_mobile = so.contact_mobile or customer.mobile_no
    contact_phone = so.contact_phone or customer.phone
    
    return {
        "name": so.name,
        "customer": so.customer,
        "customer_name": so.customer_name,
        "contact_mobile": contact_mobile,
        "contact_phone": contact_phone,
        "grand_total": so.grand_total,
        "advance_paid": so.advance_paid,
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
    outstanding = so.grand_total - so.advance_paid
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
