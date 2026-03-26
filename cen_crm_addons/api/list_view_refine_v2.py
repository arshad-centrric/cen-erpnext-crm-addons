import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Update Custom Fields (Correct Labels and List View settings)
    add_custom_fields_logic()
    
    # 2. UI Layout Adjustments via Property Setters
    apply_property_setters()
    
    frappe.db.commit()
    print("Opportunity List Layout Refined (Round 2)")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "assigned_to_name",
                "fieldtype": "Data",
                "label": "Assigned To",
                "insert_after": "naming_series",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 3
            },
            {
                "fieldname": "contact_mobile",
                "fieldtype": "Data",
                "label": "Phone", # Renamed from Contact Phone
                "insert_after": "status",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 5
            },
             {
                "fieldname": "whatsapp_link",
                "fieldtype": "Data",
                "label": "WA", # Label for the column
                "insert_after": "contact_mobile",
                "in_list_view": 1,
                "read_only": 1,
                "idx": 6
            }
        ]
    }
    # Update existing fields if they exist, or create new ones
    create_custom_fields(custom_fields, ignore_validate=True)
    print("List View Helper fields updated")

def apply_property_setters():
    # 1. Hide unwanted columns from List View
    to_remove_from_list = ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner"]
    for field in to_remove_from_list:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 2. Column Positioning using idx and in_list_view
    # Order: name (0), title (1), assigned_to_name (2), status (3), contact_mobile (4), whatsapp_link (5)
    
    # name (ID)
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
        "value": 1, # First field
        "property_type": "Int"
    })
    
    # title
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "title",
        "property": "idx",
        "value": 2,
        "property_type": "Int"
    })
    
    # status
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "status",
        "property": "idx",
        "value": 4,
        "property_type": "Int"
    })
    
    # Ensure all are in list view
    for field in ["name", "title", "assigned_to_name", "status", "contact_mobile", "whatsapp_link"]:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })

if __name__ == "__main__":
    run()
