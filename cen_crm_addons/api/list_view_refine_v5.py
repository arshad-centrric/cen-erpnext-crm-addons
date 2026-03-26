import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Ensure Custom Fields exist with correct names and labels
    add_custom_fields_logic()
    
    # 2. Strict UI Layout Adjustments
    apply_property_setters()
    
    # 3. Force metadata refresh
    frappe.clear_cache(doctype="Opportunity")
    frappe.db.commit()
    print("Opportunity List Layout Refined (Round 4 - Decisive)")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "id_display",
                "fieldtype": "Data",
                "label": "ID",
                "in_list_view": 1,
                "read_only": 1,
                "allow_on_click": 1
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
    print("Custom Fields Checked")

def apply_property_setters():
    # 1. Absolute list of fields to HIDE in List View
    # We want to be very thorough to ensure only our fields show up
    all_fields = [f.fieldname for f in frappe.get_meta("Opportunity").fields]
    wanted = ["id_display", "title", "assigned_to_name", "status", "contact_mobile", "wa_chat_link"]
    
    # Hide everything else
    for fieldname in all_fields:
        if fieldname not in wanted and fieldname != "name":
             frappe.make_property_setter({
                "doctype": "Opportunity",
                "fieldname": fieldname,
                "property": "in_list_view",
                "value": 0,
                "property_type": "Check"
            })

    # Also hide naming_series and other standard ones explicitly
    for std_field in ["naming_series", "opportunity_from", "opportunity_type", "opportunity_owner", "market_segment", "source"]:
         frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": std_field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # 2. Explicit Column Order (idx)
    # Lower idx = Leftmost
    order = {
        "id_display": 1,
        "title": 2,
        "assigned_to_name": 3,
        "status": 4,
        "contact_mobile": 5,
        "wa_chat_link": 6
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
    
    # Ensure ID (id_display) is also NOT hidden in form for debugging
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "id_display",
        "property": "hidden",
        "value": 0,
        "property_type": "Check"
    })

if __name__ == "__main__":
    run()
