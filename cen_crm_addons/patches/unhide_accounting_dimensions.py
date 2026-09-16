import frappe

def execute():
    doc_types = [
        "Sales Order", "Delivery Note", "Payment Entry", 
        "Purchase Order", "Purchase Receipt", "Purchase Invoice"
    ]
    
    frappe.db.delete("Property Setter", {
        "doc_type": ("in", doc_types),
        "field_name": "accounting_dimensions_section",
        "property": "hidden"
    })
    
    frappe.clear_cache()
