import frappe

def run():
    # 1. Hide the custom id_display from list view (redundant with standard 'name')
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "id_display",
        "property": "in_list_view",
        "value": 0,
        "property_type": "Check"
    })
    
    # 2. Ensure standard 'name' field is used as the first column and labeled 'ID'
    frappe.make_property_setter({
        "doctype": "Opportunity",
        "fieldname": "name",
        "property": "label",
        "value": "ID",
        "property_type": "Data"
    })
    
    # 3. Double-check all other fields to ensure only the wanted ones are in list view
    wanted = ["title", "assigned_to_name", "status", "contact_mobile", "wa_chat_link"]
    
    # Negative idx for these to follow the name field (which is implicitly at the start)
    # Actually, if we unset title_field, name is first.
    # Title (idx: 1), etc.
    
    order = {
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
        
    frappe.db.commit()
    frappe.clear_cache(doctype="Opportunity")
    print("Opportunity List View - Two ID Problem Fixed")

if __name__ == "__main__":
    run()
