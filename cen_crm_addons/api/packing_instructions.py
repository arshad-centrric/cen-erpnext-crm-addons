import frappe

def set_packing_instructions_from_quotation(doc, method=None):
    """
    Triggered on before_insert of Sales Order.
    Fills the Packing Instructions from the linked Quotation when the Sales Order has none.
    """
    if doc.get("custom_packing_instructions"):
        return

    quotation = next((row.prevdoc_docname for row in doc.get("items", []) if row.get("prevdoc_docname")), None)
    if not quotation:
        return

    if not frappe.get_meta("Quotation").has_field("custom_packing_instructions"):
        return

    doc.custom_packing_instructions = frappe.db.get_value("Quotation", quotation, "custom_packing_instructions")
