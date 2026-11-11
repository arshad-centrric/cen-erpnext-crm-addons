import frappe
from frappe.utils import flt
from cen_crm_addons.api.payable_amount import get_payable_amount, get_settled_amount, get_pending_amount, get_invoice_pending_amount

def update_so_payment_status(sales_order_name):
    """
    Dynamically recalculate and update custom_payment_status on a Sales Order.
    """
    so_data = frappe.db.get_value("Sales Order", sales_order_name, ["grand_total", "rounded_total", "advance_paid"], as_dict=True)
    if not so_data:
        return

    active_si = frappe.db.sql("""
        SELECT si.grand_total, si.rounded_total, si.outstanding_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus = 1
        LIMIT 1
    """, (sales_order_name,), as_dict=True)

    if active_si:
        total_amount = get_payable_amount(active_si[0])
        pending_amount = get_invoice_pending_amount(active_si[0])
    else:
        total_amount = get_payable_amount(so_data)
        pending_amount = get_pending_amount(so_data, so_data.advance_paid)

    if pending_amount <= 0.01:
        new_status = "Paid"
    elif pending_amount < total_amount:
        new_status = "Partially Paid"
    else:
        new_status = "Unpaid"
    frappe.db.set_value("Sales Order", sales_order_name, "custom_payment_status", new_status, update_modified=False)

def sync_payment_status(so_name):
    """Calculates and updates the custom_payment_status field on Sales Order."""
    if not so_name:
        return

    update_so_payment_status(so_name)

    # Auto-Close Logic (Bypassing "To Bill" trap)
    so = frappe.get_doc("Sales Order", so_name)
    settled_amount = get_settled_amount(so)
    if settled_amount > 0 and so.advance_paid >= settled_amount and so.per_delivered >= 100:
        if so.status not in ("Closed", "Cancelled"):
            so.db_set("status", "Closed", update_modified=True)
            so.add_comment("Info", "Automatically closed: Fully paid and delivered.")

def trigger_so_payment_status_update(doc, method=None):
    """
    Hook wrapper to update Sales Order payment status when Sales Invoice or Payment Entry is submitted/cancelled.
    """
    so_names = set()

    if doc.doctype == "Sales Invoice":
        for item in getattr(doc, "items", []):
            if item.get("sales_order"):
                so_names.add(item.sales_order)

    elif doc.doctype == "Payment Entry":
        for ref in getattr(doc, "references", []):
            if ref.reference_doctype == "Sales Order" and ref.reference_name:
                so_names.add(ref.reference_name)
            elif ref.reference_doctype == "Sales Invoice" and ref.reference_name:
                linked_sos = frappe.db.sql("""
                    SELECT DISTINCT sales_order
                    FROM `tabSales Invoice Item`
                    WHERE parent = %s AND sales_order IS NOT NULL AND sales_order != ''
                """, (ref.reference_name,), pluck=True)
                for so in linked_sos:
                    so_names.add(so)
        
        sync_screenshot_to_sales_order(doc)

    for so_name in so_names:
        sync_payment_status(so_name)

def on_payment_entry_update(doc, method):
    """Backwards-compatible hook wrapper for Payment Entry."""
    trigger_so_payment_status_update(doc, method)

def validate_payment_screenshot(doc, method):
    """Ensure a screenshot is attached for non-cash payments."""
    if doc.payment_type != "Receive":
        return

    if doc.mode_of_payment:
        mop_type = frappe.db.get_value("Mode of Payment", doc.mode_of_payment, "type")
        if mop_type != "Cash" and not doc.custom_payment_screenshot:
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

def on_delivery_note_update(doc, method):
    """Hook for Delivery Note to trigger status check on linked Sales Orders."""
    for item in doc.items:
        if getattr(item, "against_sales_order", None):
            sync_payment_status(item.against_sales_order)

def cancel_linked_payment_entries(doc, method=None):
    """
    Cancel the submitted Payment Entries received against a Sales Order when it is cancelled.

    Runs on before_cancel, while the Payment Entry still references the Sales Order. ERPNext's
    own cancel step only unlinks the reference and leaves the payment submitted as an advance.
    A Payment Entry that also settles other live documents (another Sales Order, an invoice)
    is left to ERPNext's default unlink, so the other documents keep their payment.
    """
    payment_entries = frappe.db.sql("""
        SELECT DISTINCT pe.name
        FROM `tabPayment Entry` pe
        JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE per.reference_doctype = 'Sales Order' AND per.reference_name = %s
            AND pe.docstatus = 1 AND pe.payment_type = 'Receive'
    """, (doc.name,), pluck=True)

    cancelled, skipped = [], []
    for pe_name in payment_entries:
        pe = frappe.get_doc("Payment Entry", pe_name)

        if _is_shared_with_live_documents(pe, doc.name):
            skipped.append(pe_name)
            continue

        pe.flags.ignore_permissions = True
        pe.cancel()
        cancelled.append(pe_name)

    if cancelled:
        # The Payment Entry cancel already reduced advance_paid in the database; keep the document in step
        # so cancelling the Sales Order does not write the old value back.
        doc.advance_paid = frappe.db.get_value("Sales Order", doc.name, "advance_paid")
        doc.add_comment("Info", "Payment Entry cancelled along with this Sales Order: " + ", ".join(cancelled))
        frappe.msgprint(
            frappe._("Payment Entries cancelled: {0}").format(", ".join(cancelled)), alert=True
        )
    if skipped:
        frappe.msgprint(
            frappe._("Payment Entries {0} also pay other documents, so they were only unlinked and not cancelled.").format(
                ", ".join(skipped)
            ),
            indicator="orange",
        )

def _is_shared_with_live_documents(payment_entry, sales_order_name):
    """True if the Payment Entry allocates to anything other than this Sales Order and cancelled Sales Orders."""
    for ref in payment_entry.references:
        if ref.reference_doctype == "Sales Order":
            if ref.reference_name == sales_order_name:
                continue
            if frappe.db.get_value("Sales Order", ref.reference_name, "docstatus") == 2:
                continue
        return True
    return False

def set_payment_status_cancelled(doc, method):
    """Ensure custom_payment_status is strictly set to Cancelled upon doc cancellation."""
    doc.db_set('custom_payment_status', 'Cancelled')
