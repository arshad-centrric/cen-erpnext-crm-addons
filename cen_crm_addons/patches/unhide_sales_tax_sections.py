import frappe

# Property Setters that hid the tax sections on Quotation, Sales Order and Payment Entry.
# They are no longer in fixtures/property_setter.json, but fixture sync never deletes a
# record that disappeared from the file, so remove them from existing sites here.
HIDDEN_TAX_SECTIONS = {
	"Quotation": ["taxes_section", "section_break_36", "section_break_39"],
	"Sales Order": ["taxes_section", "section_break_40", "section_break_43", "sec_tax_breakup"],
	"Payment Entry": ["taxes_and_charges_section"],
}


def execute():
	"""Show the tax sections again on Quotation, Sales Order and Payment Entry."""
	for doctype, fieldnames in HIDDEN_TAX_SECTIONS.items():
		for fieldname in fieldnames:
			name = f"{doctype}-{fieldname}-hidden"
			if frappe.db.exists("Property Setter", name):
				frappe.delete_doc("Property Setter", name, force=True, ignore_permissions=True)

		frappe.clear_cache(doctype=doctype)
