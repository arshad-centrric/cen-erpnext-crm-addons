import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Update Custom Fields (Adding a dedicated ID field to force List View position)
    add_custom_fields_logic()
    
    # 2. UI Layout Adjustments via Property Setters
    apply_property_setters()
    
    frappe.db.commit()
    print("Opportunity List Layout Refined (ID First Fix)")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "id_display",
                "fieldtype": "Data",
                "label": "ID",
                "insert_before": "title", # Force position in form
                "in_list_view": 1,
                "read_only": 1,
                "idx": 0
            },
            {
                "fieldname": "assigned_to_name",
                "fieldtype": "Data",
                "label": "Assigned To",
                "insert_after": "title",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 20
            },
            {
                "fieldname": "contact_mobile",
                "fieldtype": "Data",
                "label": "Phone",
                "insert_after": "status",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 30
            },
             {
                "fieldname": "whatsapp_link",
                "fieldtype": "Data",
                "label": "WA",
                "insert_after": "contact_mobile",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 40
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    print("List View Helper fields updated with ID display")

def apply_property_setters():
    # 1. Hide unwanted columns
    to_hide = ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner"]
    for field in to_hide:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 2. Position ID (id_display) as the first column
    # Frappe List View orders fields by their index (idx)
    # We will set very explicit indices
    
    fields_order = [
        ("id_display", 1),
        ("title", 2),
        ("assigned_to_name", 3),
        ("status", 4),
        ("contact_mobile", 5),
        ("whatsapp_link", 6)
    ]
    
    for field, idx in fields_order:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "idx",
            "value": idx,
            "property_type": "Int"
        })
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })

if __name__ == "__main__":
    run()
