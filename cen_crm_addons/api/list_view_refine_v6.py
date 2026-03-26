import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Renaming and Clean Up
    add_custom_fields_logic()
    
    # 2. Aggressive Property Setters
    apply_property_setters()
    
    # 3. Force Sync data to fields again
    from cen_crm_addons.api.migrate_opp_fields import run as migrate
    migrate()
    
    # 4. Clear Site Cache
    frappe.clear_cache(doctype="Opportunity")
    frappe.db.commit()
    print("Opportunity List Layout Refined (Round 5 - Decisive)")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "id_display",
                "fieldtype": "Data",
                "label": "ID",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "assigned_to_name",
                "fieldtype": "Data",
                "label": "Assigned To",
                "in_list_view": 1,
                "read_only": 1
            },
            {
                "fieldname": "contact_mobile",
                "fieldtype": "Data",
                "label": "Phone",
                "in_list_view": 1,
                "read_only": 1
            },
             {
                "fieldname": "wa_chat_link",
                "fieldtype": "Data",
                "label": "WA", 
                "in_list_view": 1,
                "read_only": 1
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    print("Custom Fields Checked (v5)")

def apply_property_setters():
    # Hide standard fields that clutter the list view
    to_hide = ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner", "market_segment", "source"]
    for std_field in to_hide:
         frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": std_field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # Forced Column Order via negative indices
    # This often forces them to the front regardless of standard fields.
    order = {
        "id_display": -10,
        "title": -8,
        "assigned_to_name": -6,
        "status": -4,
        "contact_mobile": -2,
        "wa_chat_link": 100 # Put WA at the very end
    }
    
    for fieldname, idx in order.items():
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": fieldname,
            "property": "idx",
            "value": idx,
            "property_type": "Int"
        })
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": fieldname,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })
    
    # Actually, list settings are in 'User Settings' table
    frappe.db.delete("User Settings", {"doctype": "Opportunity"})


if __name__ == "__main__":
    run()
