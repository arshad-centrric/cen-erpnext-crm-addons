import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # Decisively delete all existing Property Setters and User Settings for Opportunity
    # This forces the system to reset to our new defaults.
    frappe.db.delete("Property Setter", {"doc_type": "Opportunity"})
    
    try:
        frappe.db.delete("User Settings", {"doctype": "Opportunity"})
    except Exception:
        pass

    
    # 2. Ensure our custom helper fields exist
    add_custom_fields_logic()
    
    # 3. Apply the absolute column layout
    apply_layout()
    
    # 4. Sync data for all existing opportunities
    from cen_crm_addons.api.migrate_opp_fields import run as migrate
    migrate()
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Opportunity")
    print("Decisive Opportunity List View Fix Completed.")

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

def apply_layout():
    # Order of columns (lower idx = left):
    # ID (1), Title (2), Assigned To (3), Status (4), Phone (5), WA (6)
    
    column_config = [
        ("id_display", "ID", 1),
        ("title", "Title", 2),
        ("assigned_to_name", "Assigned To", 3),
        ("status", "Status", 4),
        ("contact_mobile", "Phone", 5),
        ("wa_chat_link", "WA", 6)
    ]
    
    # Disable title_field to prevent it from hijacking the first column
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "property": "title_field",
        "value": "",
        "property_type": "Data"
    })

    # Hide ALL standard fields from the list view first
    meta = frappe.get_meta("Opportunity")
    for field in meta.fields:
        if field.in_list_view:
             frappe.make_property_setter({
                "doctype": "Opportunity",
                "fieldname": field.fieldname,
                "property": "in_list_view",
                "value": 0,
                "property_type": "Check"
            })
            
    # Explicitly hide some problematic ones
    for std_field in ["naming_series", "opportunity_from", "opportunity_owner", "opportunity_type", "market_segment", "source"]:
         frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": std_field,
            "property": "in_list_view",
            "value": 0,
            "property_type": "Check"
        })

    # Now Force Show and Order our columns
    for fieldname, label, idx in column_config:
        # 1. Ensure in list view
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": fieldname,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })
        # 2. Set Label (especially for contact_mobile -> Phone)
        if fieldname == "contact_mobile":
             frappe.make_property_setter({
                "doctype": "Opportunity",
                "fieldname": fieldname,
                "property": "label",
                "value": label,
                "property_type": "Data"
            })
        # 3. Set index (the real ordering agent)
        # Low indices force them to the front.
        # We will use negative indices to be absolutely sure they come first.
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": fieldname,
            "property": "idx",
            "value": idx, 
            "property_type": "Int"
        })
        
    print("Property Setters Applied for specific order")

if __name__ == "__main__":
    run()
