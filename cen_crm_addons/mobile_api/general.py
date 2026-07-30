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
    
    return {
        "has_profile": 1,
        "user": doc.user,
        "full_name": doc.full_name,
        "email": doc.email,
        "is_admin_user": doc.is_admin_user or 0,
        "allowed_warehouses": [w.warehouse for w in doc.get("allowed_warehouses", [])],
        "modules": {
            "opportunity": doc.opportunity,
            "quotation": doc.quotation,
            "sales_order": doc.sales_order,
            "bom": doc.module_bom,
            "purchase_receipt_grn": doc.module_pr_grn,
            "delivery": doc.module_delivery,
            "packing": doc.module_packing,
            "Opportunities": doc.tab_opportunities,
            "Quotation": doc.tab_quotation,
            "Sales Order": doc.tab_sales_order,
            "BOM": doc.module_bom,
            "Purchase Receipt/GRN": doc.module_pr_grn,
            "Delivery": doc.module_delivery,
            "Packing": doc.module_packing
        }
    }

