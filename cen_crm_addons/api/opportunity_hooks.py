import frappe
from frappe.model.naming import make_autoname

def generate_box_id(doc, method):
    """Generates a sequential Box ID for Opportunities."""
    if not doc.get("custom_box_id"):
        doc.custom_box_id = make_autoname("B-.####")
