import frappe

@frappe.whitelist()
def get_delivery_partners(page=1, limit=20, search=""):
    """
    Fetch a paginated list of Delivery Partners.
    """
    limit_start = (int(page) - 1) * int(limit)
    limit_page_length = int(limit)
    
    filters = {}
    or_filters = {}
    
    if search:
        or_filters = {
            "name": ["like", f"%{search}%"],
            "partner_name": ["like", f"%{search}%"]
        }
        
    partners = frappe.get_all(
        "Delivery Partner",
        filters=filters,
        or_filters=or_filters,
        fields=["name", "partner_name"],
        limit_start=limit_start,
        limit_page_length=limit_page_length,
        order_by="creation desc"
    )
    
    return partners


@frappe.whitelist()
def get_mobile_user_profile():
    user = frappe.session.user
    
    if not frappe.db.exists("Mobile User Profile", user):
        return {
            "has_profile": 0,
            "message": "Mobile User Profile not found for current user.",
            "is_admin_user": 0,
            "allowed_warehouses": [],
            "modules": {}
        }
        
    doc = frappe.get_doc("Mobile User Profile", user)
    
    # 1. Active Context
    active_branch = frappe.defaults.get_user_default("branch")
    active_company = frappe.defaults.get_user_default("company") or frappe.defaults.get_user_default("cen_branch_company") or frappe.db.get_single_value("Global Defaults", "default_company")
    
    # 2. Build the Hierarchy (Companies -> Branches)
    user_branches = frappe.get_all("Branch User", filters={"user": user}, fields=["parent"])
    branch_names = [b.parent for b in user_branches]
    
    branch_docs = frappe.get_all(
        "Branch", 
        filters={"name": ["in", branch_names]}, 
        fields=["name", "custom_cen_default_company"]
    ) if branch_names else []

    companies_map = {}
    for b in branch_docs:
        company = b.custom_cen_default_company or active_company
        if company not in companies_map:
            companies_map[company] = []
        companies_map[company].append(b.name)
        
    # 3. Dynamic Child Warehouses (Mapped by Company)
    # 3. User Permitted Warehouses (Intersection Base)
    permitted_warehouses = frappe.get_all(
        "User Permission", 
        filters={"user": user, "allow": "Warehouse"}, 
        pluck="for_value"
    )
    
    permitted_child_warehouses = []
    for pw in permitted_warehouses:
        wh_details = frappe.db.get_value("Warehouse", pw, ["lft", "rgt"], as_dict=True)
        if wh_details:
            children = frappe.db.sql(
                "SELECT name FROM tabWarehouse WHERE lft > %s AND rgt < %s AND is_group = 0", 
                (wh_details.lft, wh_details.rgt), 
                as_dict=True
            )
            permitted_child_warehouses.extend([c.name for c in children])
            
    permitted_child_warehouses = set(permitted_child_warehouses)
            
    companies_hierarchy = []
    for company, branches in companies_map.items():
        branch_list = []
        for br in branches:
            branch_doc = frappe.get_doc("Branch", br)
            
            # 4. Branch-Specific Warehouses
            branch_warehouses = []
            if branch_doc.custom_cen_warehouse_parent:
                br_wh_details = frappe.db.get_value("Warehouse", branch_doc.custom_cen_warehouse_parent, ["lft", "rgt"], as_dict=True)
                if br_wh_details:
                    br_children = frappe.db.sql(
                        "SELECT name FROM tabWarehouse WHERE lft > %s AND rgt < %s AND is_group = 0", 
                        (br_wh_details.lft, br_wh_details.rgt), 
                        as_dict=True
                    )
                    br_child_names = set([c.name for c in br_children])
                    
                    # Intersect branch children with user's permitted children
                    branch_warehouses = list(br_child_names.intersection(permitted_child_warehouses))
            
            # 5. Branch-Specific Price Lists
            selling_pls = []
            if hasattr(branch_doc, "custom_cen_allowed_selling_price_lists"):
                selling_pls = [row.price_list for row in branch_doc.custom_cen_allowed_selling_price_lists if row.price_list]
            if branch_doc.custom_cen_default_selling_price_list and branch_doc.custom_cen_default_selling_price_list not in selling_pls:
                selling_pls.append(branch_doc.custom_cen_default_selling_price_list)
                
            buying_pls = []
            if hasattr(branch_doc, "custom_cen_allowed_buying_price_lists"):
                buying_pls = [row.price_list for row in branch_doc.custom_cen_allowed_buying_price_lists if row.price_list]
            if branch_doc.custom_cen_default_buying_price_list and branch_doc.custom_cen_default_buying_price_list not in buying_pls:
                buying_pls.append(branch_doc.custom_cen_default_buying_price_list)
                
            branch_list.append({
                "branch_name": br,
                "warehouses": branch_warehouses,
                "selling_price_lists": selling_pls,
                "buying_price_lists": buying_pls
            })
            
        companies_hierarchy.append({
            "company_name": company,
            "branches": branch_list
        })

    # 5. Output Format
    return {
        "has_profile": 1,
        "user": doc.user,
        "full_name": doc.full_name,
        "email": doc.email,
        "active_company": active_company,
        "active_branch": active_branch,
        "companies": companies_hierarchy,
        "is_admin_user": doc.is_admin_user or 0,
        "modules": {
            "opportunity": doc.opportunity,
            "quotation": doc.quotation,
            "sales_order": doc.sales_order,
            "bom": doc.module_bom,
            "purchase_receipt_grn": doc.module_pr_grn,
            "delivery": doc.module_delivery,
            "packing": doc.module_packing
        }
    }

