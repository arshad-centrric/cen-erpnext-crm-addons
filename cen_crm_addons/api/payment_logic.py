import frappe

def sync_payment_status(so_name):
    """Calculates and updates the custom_payment_status field on Sales Order."""
    if not so_name:
        return

    so = frappe.get_doc("Sales Order", so_name)
    
    # Calculate outstanding balance
    # ERPNext updates advance_paid when Payment Entry is submitted
    outstanding = so.grand_total - so.advance_paid
    status = "Paid" if outstanding <= 0 else "Unpaid"
    
    # Update only the specific field to avoid triggering unnecessary hooks
    so.db_set("custom_payment_status", status, update_modified=False)

def on_payment_entry_update(doc, method):
    """Hook for Payment Entry to update linked Sales Orders."""
    for ref in getattr(doc, "references", []):
        if ref.reference_doctype == "Sales Order":
            sync_payment_status(ref.reference_name)

def on_sales_order_update(doc, method):
    """Ensure status is correct whenever SO is saved."""
    sync_payment_status(doc.name)
