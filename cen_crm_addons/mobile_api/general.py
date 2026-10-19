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
def get_company_addresses(company=None, branch=None):
    """
    Fetch the active Addresses linked to a Company, for selecting the Company Address of a Quotation.
    company: Exact name of the Company (Optional, defaults to the Branch's Company, then the user's default Company)
    branch: Branch to list the addresses of (Optional, defaults to the user's active Branch. "All Branches" lists every address of the Company)
    """
    from cen_crm_addons.api.company_address import get_company_address_list

    resolved_branch = branch or frappe.defaults.get_user_default("branch")
    resolved_branch = str(resolved_branch).strip() if resolved_branch else None
    if resolved_branch == "All Branches":
        resolved_branch = None

    if resolved_branch and not frappe.db.exists("Branch", resolved_branch):
        frappe.throw(f"Branch {resolved_branch} not found")

    company = str(company).strip() if company else None
    if not company and resolved_branch:
        company = frappe.db.get_value("Branch", resolved_branch, "custom_cen_default_company")
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")

    if not company:
        frappe.throw("Company is a required parameter")

    if not frappe.db.exists("Company", company):
        frappe.throw(f"Company {company} not found")

    return get_company_address_list(company, resolved_branch)


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

    # Branch logic lives in cen_branch_management; imported here so this
    # module still loads on sites that don't have that app.
    from cen_branch_management.api.switcher import resolve_login_branch
    from cen_branch_management.api.warehouse_access import get_user_branch_warehouses, get_user_default_warehouse

    fallback_company = frappe.defaults.get_user_default("company") or frappe.db.get_single_value("Global Defaults", "default_company")

    # 1. The user's branches, ordered by company then branch, so "the first
    # branch in the list" below is stable.
    branch_names = frappe.get_all("Branch User", filters={"user": user, "parenttype": "Branch"}, pluck="parent")
    branch_docs = frappe.get_all(
        "Branch",
        filters={"name": ["in", branch_names]},
        fields=["name", "custom_cen_default_company"],
        order_by="custom_cen_default_company asc, name asc",
    ) if branch_names else []

    # 2. Warehouses per branch: what the branch allows this user (their
    # Restricted Warehouses on that branch, else everything under its
    # Warehouse Parent), kept to what their Warehouse user permissions allow
    # so the app never offers a warehouse the server would refuse.
    permitted_warehouses = _get_permitted_warehouses(user)

    companies_map = {}
    for b in branch_docs:
        company = b.custom_cen_default_company or fallback_company
        branch_doc = frappe.get_doc("Branch", b.name)

        branch_warehouses = get_user_branch_warehouses(branch_doc, user)
        if permitted_warehouses is not None:
            branch_warehouses = [w for w in branch_warehouses if w in permitted_warehouses]

        # The warehouse new documents should start with on this branch, for
        # this user: the branch's Default Warehouse, or for a user restricted
        # away from it, their first allowed one. Only ever one of the listed
        # warehouses; None means the branch has no default for this user.
        default_warehouse = get_user_default_warehouse(branch_doc, user, branch_warehouses)
        if default_warehouse not in branch_warehouses:
            default_warehouse = None

        # Branch-Specific Price Lists
        selling_pls = [row.price_list for row in branch_doc.get("custom_cen_allowed_selling_price_lists") or [] if row.price_list]
        if branch_doc.custom_cen_default_selling_price_list and branch_doc.custom_cen_default_selling_price_list not in selling_pls:
            selling_pls.append(branch_doc.custom_cen_default_selling_price_list)

        buying_pls = [row.price_list for row in branch_doc.get("custom_cen_allowed_buying_price_lists") or [] if row.price_list]
        if branch_doc.custom_cen_default_buying_price_list and branch_doc.custom_cen_default_buying_price_list not in buying_pls:
            buying_pls.append(branch_doc.custom_cen_default_buying_price_list)

        companies_map.setdefault(company, []).append({
            "branch_name": b.name,
            "warehouses": [
                {"warehouse": warehouse, "is_default": 1 if warehouse == default_warehouse else 0}
                for warehouse in branch_warehouses
            ],
            "selling_price_lists": selling_pls,
            "buying_price_lists": buying_pls
        })

    companies_hierarchy = [
        {"company_name": company, "branches": branches} for company, branches in companies_map.items()
    ]

    # 3. Active branch and company: the user's Default Branch from the User
    # master (when it still exists and they are still assigned to it), else
    # the first branch in the list above. The company is that branch's.
    active_branch = resolve_login_branch(user)
    if not active_branch and companies_hierarchy:
        active_branch = companies_hierarchy[0]["branches"][0]["branch_name"]

    active_company = (
        frappe.db.get_value("Branch", active_branch, "custom_cen_default_company") if active_branch else None
    ) or fallback_company

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


def _get_permitted_warehouses(user):
    """Warehouses the user's Warehouse user permissions allow (each permitted
    warehouse and everything under it), or None when they have none -- which
    in Frappe means no warehouse restriction at all."""
    from frappe.core.doctype.user_permission.user_permission import get_user_permissions

    permissions = get_user_permissions(user).get("Warehouse")
    if not permissions:
        return None

    return {permission.doc for permission in permissions}
