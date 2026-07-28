import frappe

def generate_box_id(doc, method):
    """Generates a sequential Box ID for Opportunities using Cen CRM Settings."""
    if doc.get("custom_box_id"):
        return

    settings = frappe.db.get_value(
        "Cen CRM Settings", 
        "Cen CRM Settings", 
        ["box_id_prefix", "current_box_id_number"], 
        as_dict=True
    ) or {}

    prefix = settings.get("box_id_prefix") or "B"
    try:
        current_num = int(settings.get("current_box_id_number") or 0)
    except (ValueError, TypeError):
        current_num = 0

    next_number = current_num + 1
    doc.custom_box_id = f"{prefix}-{str(next_number).zfill(4)}"

    frappe.db.set_value("Cen CRM Settings", "Cen CRM Settings", "current_box_id_number", next_number)
