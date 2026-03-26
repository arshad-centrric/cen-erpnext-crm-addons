import frappe

def get_manager_roles():
    return ["System Manager", "Administrator", "Sales Manager"]

def get_sales_person_role():
    return "Sales Person"

def has_manager_role(user):
    user_roles = frappe.get_roles(user)
    manager_roles = get_manager_roles()
    
    for role in manager_roles:
        if role in user_roles:
            return True
            
    return False

def is_sales_person(user):
    return get_sales_person_role() in frappe.get_roles(user)

def lead_query(user):
    if not user:
        user = frappe.session.user

    if has_manager_role(user):
        return ""
        
    if is_sales_person(user):
        return """(
            `tabLead`.lead_owner = '{user}' OR 
            `tabLead`.owner = '{user}' OR
            `tabLead`.name IN (
                SELECT reference_name FROM `tabToDo` 
                WHERE reference_type='Lead' 
                AND allocated_to='{user}'
            ) OR
            `tabLead`.name IN (
                SELECT party_name FROM `tabOpportunity`
                WHERE name IN (
                    SELECT reference_name FROM `tabToDo`
                    WHERE reference_type='Opportunity'
                    AND allocated_to='{user}'
                )
            )
        )""".format(user=user)
        
    return ""

def lead_has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    # Allow creation
    if ptype == "create" or getattr(doc, "is_new", lambda: False)():
        return True

    if has_manager_role(user):
        return True
        
    if is_sales_person(user):
        if doc.lead_owner == user or doc.owner == user:
            return True
            
        # Check if directly assigned to this lead
        is_assigned = frappe.db.exists("ToDo", {
            "reference_type": "Lead",
            "reference_name": doc.name,
            "allocated_to": user
        })

        # Check if ever assigned to a linked Opportunity
        linked_opp_assigned = frappe.db.sql("""
            SELECT name FROM `tabToDo`
            WHERE reference_type='Opportunity'
            AND allocated_to=%s
            AND reference_name IN (
                SELECT name FROM `tabOpportunity` WHERE party_name=%s
            )
        """, (user, doc.name))
        
        if is_assigned or linked_opp_assigned:
            return True
            
        return False
        
    return True

def opportunity_query(user):
    if not user:
        user = frappe.session.user

    if has_manager_role(user):
        return ""
        
    if is_sales_person(user):
        return """(
            `tabOpportunity`.opportunity_owner = '{user}' OR 
            `tabOpportunity`.owner = '{user}' OR
            `tabOpportunity`.name IN (
                SELECT reference_name FROM `tabToDo` 
                WHERE reference_type='Opportunity' 
                AND allocated_to='{user}'
            )
        )""".format(user=user)
        
    return ""

def opportunity_has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    # Allow creation
    if ptype == "create" or getattr(doc, "is_new", lambda: False)():
        return True

    if has_manager_role(user):
        return True
        
    if is_sales_person(user):
        # The opportunity_owner field is standard in ERPNext
        if getattr(doc, "opportunity_owner", None) == user or doc.owner == user:
            return True
            
        # Check if ever assigned
        is_assigned = frappe.db.exists("ToDo", {
            "reference_type": "Opportunity",
            "reference_name": doc.name,
            "allocated_to": user
        })
        
        if is_assigned:
            return True
            
        return False
        
    return True

def prospect_query(user):
    if not user:
        user = frappe.session.user

    if has_manager_role(user):
        return ""
        
    if is_sales_person(user):
        return """(
            `tabProspect`.prospect_owner = '{user}' OR 
            `tabProspect`.owner = '{user}' OR
            `tabProspect`.name IN (
                SELECT reference_name FROM `tabToDo` 
                WHERE reference_type='Prospect' 
                AND allocated_to='{user}'
            )
        )""".format(user=user)
        
    return ""

def prospect_has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user

    # Allow creation
    if ptype == "create" or getattr(doc, "is_new", lambda: False)():
        return True

    if has_manager_role(user):
        return True
        
    if is_sales_person(user):
        if getattr(doc, "prospect_owner", None) == user or doc.owner == user:
            return True
            
        # Check if ever assigned
        is_assigned = frappe.db.exists("ToDo", {
            "reference_type": "Prospect",
            "reference_name": doc.name,
            "allocated_to": user
        })
        
        if is_assigned:
            return True
            
        return False
        
    return True

def update_whatsapp_link(doc, method=None):
    if doc.mobile_no:
        phone = "".join(filter(str.isdigit, doc.mobile_no))
        if phone:
            doc.whatsapp_link = f"https://wa.me/{phone}"
    
    # Also sync for the new list view logic
    sync_lead_list_fields(doc)

def sync_lead_list_fields(doc, method=None):
    # 1. Update Assigned To Name (Fetch from ToDo)
    todo = frappe.db.get_value("ToDo", 
        {"reference_type": "Lead", "reference_name": doc.name, "status": "Open"}, 
        "allocated_to"
    )
    if todo:
        doc.assigned_to_name = frappe.db.get_value("User", todo, "full_name") or todo
            
    # 2. Sync WhatsApp Link for the new list view field
    if doc.mobile_no:
        phone = "".join(filter(str.isdigit, doc.mobile_no))
        if phone:
            doc.wa_chat_link = f"https://wa.me/{phone}"


def sync_opportunity_list_fields(doc, method=None):
    # 0. Update ID for the first column
    doc.id_display = doc.name
    
    # 1. Update Assigned To Name (Fetch from ToDo)
    todo = frappe.db.get_value("ToDo", 
        {"reference_type": "Opportunity", "reference_name": doc.name, "status": "Open"}, 
        "allocated_to"
    )
    if todo:
        doc.assigned_to_name = frappe.db.get_value("User", todo, "full_name") or todo
            
    # 2. Update Contact Mobile
    # For Leads
    if doc.opportunity_from == "Lead" and doc.party_name:
        doc.contact_mobile = frappe.db.get_value("Lead", doc.party_name, "mobile_no")
    # For Customers
    elif doc.opportunity_from == "Customer" and doc.party_name:
        contact_mobile = frappe.db.sql("""
            SELECT c.mobile_no 
            FROM `tabContact` c
            JOIN `tabDynamic Link` l ON l.parent = c.name
            WHERE l.link_doctype = 'Customer' AND l.link_name = %s
            LIMIT 1
        """, doc.party_name)
        if contact_mobile:
            doc.contact_mobile = contact_mobile[0][0]
    
    # 3. Sync WhatsApp Link also for the new list view field
    if doc.contact_mobile:
        phone = "".join(filter(str.isdigit, doc.contact_mobile))
        if phone:
            doc.wa_chat_link = f"https://wa.me/{phone}"



