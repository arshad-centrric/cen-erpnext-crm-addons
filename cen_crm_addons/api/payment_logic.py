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
    
    # Sync screenshot to the first Sales Order reference if it exists
    sync_screenshot_to_sales_order(doc)

def validate_payment_screenshot(doc, method):
    """Ensure a screenshot is attached for non-cash payments."""
    if doc.payment_type != "Receive":
        return

    if doc.mode_of_payment != "Cash" and not doc.custom_payment_screenshot:
        frappe.throw(
            msg="Payment screenshot is mandatory for non-cash transactions.",
            title="Attachment Required"
        )

def sync_screenshot_to_sales_order(doc):
    """Attaches the Payment Entry screenshot to the linked Sales Order."""
    if not doc.custom_payment_screenshot:
        return

    # Find the first Sales Order reference
    so_name = None
    for ref in getattr(doc, "references", []):
        if ref.reference_doctype == "Sales Order":
            so_name = ref.reference_name
            break # Only sync to the first one as per user requirement
    
    if not so_name:
        return

    # Check if already attached to avoid duplicates
    existing_file = frappe.db.exists("File", {
        "attached_to_doctype": "Sales Order",
        "attached_to_name": so_name,
        "file_url": doc.custom_payment_screenshot
    })

    if not existing_file:
        frappe.get_doc({
            "doctype": "File",
            "file_url": doc.custom_payment_screenshot,
            "attached_to_doctype": "Sales Order",
            "attached_to_name": so_name,
            "is_private": 1
        }).insert(ignore_permissions=True)
        
        # Optional: Add a comment to the SO timeline
        so_doc = frappe.get_doc("Sales Order", so_name)
        so_doc.add_comment("Attachment", "Payment screenshot synced from " + doc.name)

def on_sales_order_update(doc, method):
    """Ensure status is correct whenever SO is saved."""
    sync_payment_status(doc.name)
