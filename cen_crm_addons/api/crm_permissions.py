import frappe

def get_manager_roles():
    return ["System Manager", "Administrator", "Sales Manager", "Supervisor"]

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
        limit=1,
        ignore_permissions=True
    )
    if todo:
        assigned_user = todo[0].allocated_to
        doc.custom_assigned_to = assigned_user
        
        # Also sync full name for UI readability
        full_name = frappe.db.get_value("User", assigned_user, "full_name")
        doc.custom_assigned_full_name = full_name if full_name else assigned_user
    else:
        # Only clear if it was previously set in the database (prevents clearing during first insert)
        if doc.get_db_value("custom_assigned_to"):
            doc.custom_assigned_to = ""
            doc.custom_assigned_full_name = ""

            
    # 2. Sync WhatsApp Link (Ground truth mobile_no)
    if doc.mobile_no:
        phone = "".join(filter(str.isdigit, doc.mobile_no))
        if phone:
            doc.custom_wa_chat_link = f"https://wa.me/{phone}"
    else:
        doc.custom_wa_chat_link = ""

def sync_opportunity_list_fields(doc, method=None):
    # 0. Sync basic fields from lead if blank
    if doc.opportunity_from == "Lead" and doc.party_name:
        lead_data = frappe.get_cached_value("Lead", doc.party_name, ["mobile_no", "city", "state", "country"], as_dict=True)
        if lead_data:
            # Sync mobile
            if not getattr(doc, 'contact_mobile', None):
                doc.contact_mobile = lead_data.mobile_no
            
            # Sync Address fields if blank
            if not doc.custom_delivery_city:
                doc.custom_delivery_city = lead_data.city
            if not doc.custom_delivery_state:
                doc.custom_delivery_state = lead_data.state
            if not doc.custom_delivery_country:
                doc.custom_delivery_country = lead_data.country

    # 1. Update Assigned To (Fetch from ToDo)
    todo = frappe.get_all("ToDo", 
        filters={"reference_type": "Opportunity", "reference_name": doc.name, "status": "Open"},
        fields=["allocated_to"],
        order_by="creation desc",
        limit=1,
        ignore_permissions=True
    )
    if todo:
        assigned_user = todo[0].allocated_to
        doc.custom_assigned_to = assigned_user
        
        # Also sync full name for UI readability
        full_name = frappe.db.get_value("User", assigned_user, "full_name")
        doc.custom_assigned_full_name = full_name if full_name else assigned_user
    else:
        # Only clear if it was previously set in the database (prevents clearing during first insert)
        if doc.get_db_value("custom_assigned_to"):
            doc.custom_assigned_to = ""
            doc.custom_assigned_full_name = ""
            
    # 2. Sync WhatsApp Link (Ground truth contact_mobile)
    mobile = getattr(doc, 'contact_mobile', None)
    if mobile:
        phone = "".join(filter(str.isdigit, mobile))
        if phone:
            doc.custom_wa_chat_link = f"https://wa.me/{phone}"
    else:
        doc.custom_wa_chat_link = ""

    # 3. Create/Update Standard Address (Cross-Doc Sync)
    if doc.custom_address_line_1 and doc.custom_delivery_city:
        sync_opportunity_to_address(doc)

def sync_opportunity_to_address(doc):
    """Creates or updates a standard Address record from Opportunity custom fields."""
    if not doc.party_name:
        return

    party_type = doc.opportunity_from
    party_name = doc.party_name

    # 1. Search for an address already officially linked to this specific Opportunity
    existing_address = frappe.db.get_value("Dynamic Link", {
        "link_doctype": "Opportunity",
        "link_name": doc.name,
        "parenttype": "Address"
    }, "parent")

    # 2. If it exists, update it
    if existing_address:
        address_doc = frappe.get_doc("Address", existing_address)
        address_doc.update({
            "address_line1": doc.custom_address_line_1,
            "address_line2": doc.custom_address_line_2,
            "city": doc.custom_delivery_city,
            "state": doc.custom_delivery_state,
            "pincode": doc.custom_pincode,
            "country": doc.custom_delivery_country
        })
        address_doc.save(ignore_permissions=True)
        return

    # 3. If no link exists, check if any Address with this content exists for this Lead/Customer
    # (Optional: this prevents duplicate addresses if multiple people have the same address)
    match_by_content = frappe.db.get_value("Address", {
        "address_line1": doc.custom_address_line_1,
        "city": doc.custom_delivery_city,
        "address_type": "Billing"
    }, "name")

    if match_by_content:
        address_doc = frappe.get_doc("Address", match_by_content)
        # Link this new Opportunity to the matched address
        address_doc.append("links", {
            "link_doctype": "Opportunity",
            "link_name": doc.name
        })
        address_doc.save(ignore_permissions=True)
        return

    # 4. If nothing else fits, create a new Address record
    address_title = frappe.db.get_value(party_type, party_name, "customer_name" if party_type=="Customer" else "lead_name") or party_name
    
    new_address = frappe.get_doc({
        "doctype": "Address",
        "address_title": address_title,
        "address_type": "Billing",
        "address_line1": doc.custom_address_line_1,
        "address_line2": doc.custom_address_line_2,
        "city": doc.custom_delivery_city,
        "state": doc.custom_delivery_state,
        "pincode": doc.custom_pincode,
        "country": doc.custom_delivery_country,
        "links": [
            {
                "link_doctype": party_type,
                "link_name": party_name
            },
            {
                "link_doctype": "Opportunity",
                "link_name": doc.name
            }
        ]
    })
    new_address.insert(ignore_permissions=True)

def item_query(user):
    # Filter out customized/one-off items from standard searches
    if frappe.db.has_column("Item", "custom_is_customized_bundle"):
        return "`tabItem`.custom_is_customized_bundle = 0 OR `tabItem`.custom_is_customized_bundle IS NULL"
    return ""
