import frappe
from frappe import _

def get_delivery_charge_item():
    """Returns the Delivery Charge Item configured in Cen CRM Settings (or None)."""
    return frappe.db.get_single_value("Cen CRM Settings", "delivery_charge_item") or None

def set_delivery_charge_flags(doc, method=None):
    """
    Triggered on validate of Opportunity.
    Marks the Delivery Charge row and the parent document, and blocks duplicates.
    Flags are always derived from the items table, so values sent by any client are ignored.
    """
    delivery_item = get_delivery_charge_item()
    delivery_rows = []

    for row in doc.get("items") or []:
        is_delivery_charge = 1 if delivery_item and row.item_code == delivery_item else 0
        row.custom_is_delivery_charge = is_delivery_charge
        if is_delivery_charge:
            delivery_rows.append(row)

    if len(delivery_rows) > 1:
        frappe.throw(
            msg=_("Delivery Charge Item {0} can be added only once. It is repeated in rows: {1}.").format(
                frappe.bold(delivery_item), ", ".join(str(row.idx) for row in delivery_rows)
            ),
            title=_("Duplicate Delivery Charge")
        )

    doc.custom_has_delivery_charge = 1 if delivery_rows else 0
