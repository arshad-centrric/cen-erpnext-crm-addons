import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Clear Lead Property Setters and User Settings to start fresh
    frappe.db.delete("Property Setter", {"doc_type": "Lead"})
    try:
        frappe.db.delete("User Settings", {"doctype": "Lead"})
    except Exception:
        pass

    # 2. Ensure custom fields exist on Lead
    add_custom_fields_logic()
    
    # 3. Apply the 1-6 layout for Lead
    apply_layout()
    
    # 4. Sync all existing leads
    sync_existing_leads()
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Lead")
    print("Lead List View Decisive Fix (Replication) Completed.")

def add_custom_fields_logic():
    custom_fields = {
        "Lead": [
            {
                "fieldname": "assigned_to_name",
                "fieldtype": "Data",
                "label": "Assigned To",
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
    print("Lead Custom Fields Added")

def apply_layout():
    # Col Order:
    # 1. name (ID)
    # 2. lead_name (Title)
    # 3. assigned_to_name (Assigned To)
    # 4. status (Status)
    # 5. mobile_no (Phone)
    # 6. wa_chat_link (WA)
    
    column_config = [
        ("name", "ID", 1),
        ("lead_name", "Title", 2),
        ("assigned_to_name", "Assigned To", 3),
        ("status", "Status", 4),
        ("mobile_no", "Phone", 5),
        ("wa_chat_link", "WA", 6)
    ]
    
    # Unset lead's title_field
    frappe.make_property_setter({
        "doctype": "Lead",
        "property": "title_field",
        "value": "",
        "property_type": "Data"
    })

    # Hide ALL standard fields from the list view first
    meta = frappe.get_meta("Lead")
    for field in meta.fields:
        if field.in_list_view:
             frappe.make_property_setter({
                "doctype": "Lead",
                "fieldname": field.fieldname,
                "property": "in_list_view",
                "value": 0,
                "property_type": "Check"
            })

    # Now Force Show and Order our columns
    for fieldname, label, idx in column_config:
        frappe.make_property_setter({
            "doctype": "Lead",
            "fieldname": fieldname,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })
        # Set label for Phone
        if fieldname == "mobile_no":
             frappe.make_property_setter({
                "doctype": "Lead",
                "fieldname": fieldname,
                "property": "label",
                "value": label,
                "property_type": "Data"
            })
        frappe.make_property_setter({
            "doctype": "Lead",
            "fieldname": fieldname,
            "property": "idx",
            "value": idx, 
            "property_type": "Int"
        })
    print("Lead Layout Property Setters Applied")

def sync_existing_leads():
    from cen_crm_addons.api.crm_permissions import sync_lead_list_fields
    leads = frappe.get_all("Lead")
    print(f"Syncing {len(leads)} leads...")
    for l in leads:
        lead_doc = frappe.get_doc("Lead", l.name)
        sync_lead_list_fields(lead_doc)
        lead_doc.db_update()
    print("Lead Sync Complete")

if __name__ == "__main__":
    run()
