import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    # 1. Update Status Options
    update_statuses()
    
    # 2. Add Custom Fields (Delivery & WhatsApp)
    add_custom_fields_logic()
    
    # 3. UI Tweaks (Hide fields & List View columns)
    apply_property_setters()
    
    frappe.db.commit()
    print("Phase 2 Implementation Complete")

def update_statuses():
    # Opportunity Statuses
    opp_meta = frappe.get_meta("Opportunity")
    opp_status_field = opp_meta.get_field("status")
    opp_options = opp_status_field.options.split("\n")
    if "Ready to Quote" not in opp_options:
        opp_options.insert(opp_options.index("Open") + 1, "Ready to Quote")
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": "status",
            "property": "options",
            "value": "\n".join(opp_options),
            "property_type": "Text"
        })
        print("Added 'Ready to Quote' to Opportunity")

    # Lead Statuses
    lead_meta = frappe.get_meta("Lead")
    lead_status_field = lead_meta.get_field("status")
    lead_options = lead_status_field.options.split("\n")
    if "Ready to Quote" not in lead_options:
        lead_options.insert(lead_options.index("Open") + 1, "Ready to Quote")
        frappe.make_property_setter({
            "doctype": "Lead",
            "fieldname": "status",
            "property": "options",
            "value": "\n".join(lead_options),
            "property_type": "Text"
        })
        print("Added 'Ready to Quote' to Lead")

def add_custom_fields_logic():
    custom_fields = {
        "Opportunity": [
            {
                "fieldname": "delivery_details_section",
                "fieldtype": "Section Break",
                "label": "Delivery Details",
                "insert_after": "items"
            },
            {
                "fieldname": "delivery_warehouse",
                "fieldtype": "Link",
                "label": "Delivery Warehouse",
                "options": "Warehouse",
                "insert_after": "delivery_details_section"
            },
            {
                "fieldname": "mode_of_delivery",
                "fieldtype": "Select",
                "label": "Mode of Delivery",
                "options": "Airport\nPick up from store\nCourier",
                "insert_after": "delivery_warehouse"
            },
            {
                "fieldname": "delivery_date",
                "fieldtype": "Date",
                "label": "Delivery Date",
                "insert_after": "mode_of_delivery"
            },
            {
                "fieldname": "delivery_time",
                "fieldtype": "Time",
                "label": "Delivery Time",
                "insert_after": "delivery_date"
            },
            {
                "fieldname": "whatsapp_link",
                "fieldtype": "Data",
                "label": "WhatsApp Link",
                "insert_after": "mobile_no",
                "in_list_view": 1,
                "read_only": 1
            }
        ],
        "Lead": [
            {
                "fieldname": "whatsapp_link",
                "fieldtype": "Data",
                "label": "WhatsApp Link",
                "insert_after": "mobile_no",
                "in_list_view": 1,
                "read_only": 1
            }
        ]
    }
    create_custom_fields(custom_fields, ignore_validate=True)
    print("Custom fields added/updated")

def apply_property_setters():
    # Hide fields in Opportunity
    to_hide_opp = ["opportunity_from", "party_name", "opportunity_type", "order_type", "sales_stage", "probability", "naming_series"]
    for fieldname in to_hide_opp:
        df = frappe.get_meta("Opportunity").get_field(fieldname)
        if df and not df.reqd:
            frappe.make_property_setter({
                "doctype": "Opportunity",
                "fieldname": fieldname,
                "property": "hidden",
                "value": 1,
                "property_type": "Check"
            })
    
    # List View Column Setup for Opportunity
    # Order: title, mobile_no, owner, name (ID), status, whatsapp_link
    opp_list_cols = [
        ("title", 1),
        ("mobile_no", 2),
        ("owner", 3),
        ("name", 4),
        ("status", 5),
        ("whatsapp_link", 6)
    ]
    for field, idx in opp_list_cols:
        frappe.make_property_setter({
            "doctype": "Opportunity",
            "fieldname": field,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })
        # Note: idx Property Setter is for the field order in the form usually, 
        # but in v15 list view uses the order of fields with in_list_view=1.
    
    # Hide fields in Lead
    to_hide_lead = ["lead_source", "lead_owner", "industry", "market_segment", "request_type"]
    for fieldname in to_hide_lead:
        df = frappe.get_meta("Lead").get_field(fieldname)
        if df and not df.reqd:
            frappe.make_property_setter({
                "doctype": "Lead",
                "fieldname": fieldname,
                "property": "hidden",
                "value": 1,
                "property_type": "Check"
            })
            
    # List View Column Setup for Lead
    # Order: first_name, mobile_no, owner, name (ID), status, whatsapp_link
    lead_list_cols = [
        ("first_name", 1),
        ("mobile_no", 2),
        ("owner", 3),
        ("name", 4),
        ("status", 5),
        ("whatsapp_link", 6)
    ]
    for field, idx in lead_list_cols:
        frappe.make_property_setter({
            "doctype": "Lead",
            "fieldname": field,
            "property": "in_list_view",
            "value": 1,
            "property_type": "Check"
        })

    print("UI Minimization applied")

if __name__ == "__main__":
    run()
