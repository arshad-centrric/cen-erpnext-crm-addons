import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Update Custom Fields (Renaming field to avoid conflicts)
    add_custom_fields_logic()
    
    # 2. UI Layout Adjustments via Property Setters
    apply_property_setters()
    
    frappe.db.commit()
    print("Opportunity List Layout Refined (v4 - Conflict Fix)")

def add_custom_fields_logic():
    # Delete old field first to be clean
    frappe.db.delete("Custom Field", {"dt": "Opportunity", "fieldname": "whatsapp_link"})
    
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "id_display",
                "fieldtype": "Data",
                "label": "ID",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 0
            },
             {
                "fieldname": "wa_chat_link", # Renamed from whatsapp_link
                "fieldtype": "Data",
                "label": "WA", 
                "in_list_view": 1,
                "read_only": 1,
                "idx": 99 # Push to end
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    print("List View Helper fields updated (v4)")

def apply_property_setters():
    # 1. Hide unwanted columns
    to_hide = ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner", "whatsapp_link"]
    for field in to_hide:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 2. Position ID (id_display) as the first column
    fields_order = [
        ("id_display", 1),
        ("title", 2),
        ("assigned_to_name", 3),
        ("status", 4),
        ("contact_mobile", 5),
        ("wa_chat_link", 100)
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
