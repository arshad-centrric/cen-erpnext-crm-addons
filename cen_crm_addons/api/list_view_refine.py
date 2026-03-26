import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Update Custom Fields (Adding List View Helpers)
    add_custom_fields_logic()
    
    # 2. UI Layout Adjustments via Property Setters
    apply_property_setters()
    
    frappe.db.commit()
    print("Opportunity List Layout Refined")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "assigned_to_name",
                "fieldtype": "Data",
                "label": "Assigned To",
                "insert_after": "naming_series",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "contact_mobile",
                "fieldtype": "Data",
                "label": "Contact Phone",
                "insert_after": "status",
                "in_list_view": 1,
                "read_only": 1
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    print("List View Helper fields added")

def apply_property_setters():
    # 1. Remove unwanted columns from List View
    to_remove_from_list = ["naming_series", "opportunity_from", "opportunity_type"]
    for field in to_remove_from_list:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 2. Position ID (name) as First Column
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "name",
        "property": "in_list_view",
        "value": 1,
        "property_type": "Check"
    })
    
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "name",
        "property": "idx",
        "value": 0,
        "property_type": "Int"
    })
    
    # Other important columns must be in list view
    for field in ["title", "status", "assigned_to_name", "contact_mobile", "whatsapp_link"]:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })

if __name__ == "__main__":
    run()
