import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Ensure Custom Fields exist 
    add_custom_fields_logic()
    
    # 2. Aggressive Property Setters
    apply_property_setters()
    
    # 3. Force Sync data to fields
    from cen_crm_addons.api.migrate_opp_fields import run as migrate
    migrate()
    
    # 4. Clear Site Cache
    frappe.clear_cache(doctype="Opportunity")
    frappe.db.commit()
    print("Opportunity List Layout Refined (Round 6 - Title Field Fix)")

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

def apply_property_setters():
    # 1. Unset Title Field to prevent it from overriding ID
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "property": "title_field",
        "value": "", # Unset it
        "property_type": "Data"
    })

    # 2. Hide unwanted fields
    to_hide = ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner", "market_segment", "source"]
    for std_field in to_hide:
         frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": std_field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 3. Forced Column Order via explicit indices
    order = {
        "id_display": 1,
        "title": 2,
        "assigned_to_name": 3,
        "status": 4,
        "contact_mobile": 5,
        "wa_chat_link": 100
    }
    
    # Reset all in_list_view first to 0 if they are not in our list
    meta = frappe.get_meta("Opportunity")
    for f in meta.fields:
        if f.fieldname not in order and f.in_list_view:
             frappe.make_property_setter({
                "doctype": "Opportunity",
                "fieldname": f.fieldname,
                "property": "in_list_view",
                "value": 0,
                "property_type": "Check"
            })

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

if __name__ == "__main__":
    run()
