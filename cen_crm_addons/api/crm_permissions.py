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

def sync_lead_list_fields(doc, method=None):
    # 1. Update Assigned To Name (Fetch from ToDo)
    todo = frappe.get_all("ToDo", 
        filters={"reference_type": "Lead", "reference_name": doc.name, "status": "Open"},
        fields=["allocated_to"],
        order_by="creation desc",
        limit=1
    )
    if todo:
        doc.custom_assigned_to = todo[0].allocated_to
    else:
        doc.custom_assigned_to = ""
            
    # 2. Sync WhatsApp Link (Ground truth mobile_no)
    if doc.mobile_no:
        phone = "".join(filter(str.isdigit, doc.mobile_no))
        if phone:
            doc.custom_wa_chat_link = f"https://wa.me/{phone}"
    else:
        doc.custom_wa_chat_link = ""

def sync_opportunity_list_fields(doc, method=None):
    # 0. Sync mobile_no from lead if blank
    if not getattr(doc, 'contact_mobile', None) and doc.opportunity_from == "Lead" and doc.party_name:
        doc.contact_mobile = frappe.get_cached_value("Lead", doc.party_name, "mobile_no")

    # 1. Update Assigned To (Fetch from ToDo)
    todo = frappe.get_all("ToDo", 
        filters={"reference_type": "Opportunity", "reference_name": doc.name, "status": "Open"},
        fields=["allocated_to"],
        order_by="creation desc",
        limit=1
    )
    if todo:
        doc.custom_assigned_to = todo[0].allocated_to
    else:
        doc.custom_assigned_to = ""
            
    # 2. Sync WhatsApp Link (Ground truth contact_mobile)
    mobile = getattr(doc, 'contact_mobile', None)
    if mobile:
        phone = "".join(filter(str.isdigit, mobile))
        if phone:
            doc.custom_wa_chat_link = f"https://wa.me/{phone}"
    else:
        doc.custom_wa_chat_link = ""



