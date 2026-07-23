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
def get_payment_attachments(sales_order):
    """
    Fetch all Payment Entries and their file attachments linked to a specific Sales Order.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required.")
        
    # Find all Payment Entries linked to this Sales Order
    payment_references = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "reference_doctype": "Sales Order",
            "reference_name": sales_order,
            "docstatus": 1
        },
        fields=["parent", "allocated_amount"]
    )
    
    pe_ids = [ref.parent for ref in payment_references]
    
    if not pe_ids:
        return []
        
    # Fetch Payment Entry core details
    payment_entries = frappe.get_all(
        "Payment Entry",
        filters={"name": ["in", pe_ids]},
        fields=["name", "posting_date", "mode_of_payment", "paid_amount"]
    )
        
    # Query standard sidebar File attachments
    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Payment Entry",
            "attached_to_name": ["in", pe_ids]
        },
        fields=["file_url", "file_name", "attached_to_name"]
    )
    
    # Map attachments to Payment Entries
    response = []
    
    for pe in payment_entries:
        pe_attachments = []
        
        # Standard sidebar files
        for f in files:
            if f.attached_to_name == pe.name:
                pe_attachments.append({
                    "file_url": f.file_url,
                    "file_name": f.file_name
                })
                
        # Find allocated amount from references
        allocated = 0
        for ref in payment_references:
            if ref.parent == pe.name:
                allocated = ref.allocated_amount
                break
                
        response.append({
            "payment_entry": pe.name,
            "posting_date": pe.posting_date,
            "mode_of_payment": pe.mode_of_payment,
            "paid_amount": pe.paid_amount,
            "allocated_amount": allocated,
            "attachments": pe_attachments
        })
            
    return response

@frappe.whitelist()
def get_mobile_user_profile():
    user = frappe.session.user
    
    if not frappe.db.exists("Mobile User Profile", user):
        return {
            "has_profile": 0,
            "message": "Mobile User Profile not found for current user.",
            "allowed_warehouses": [],
            "modules": {},
            "sub_tabs": {}
        }
        
    doc = frappe.get_doc("Mobile User Profile", user)
    
    return {
        "has_profile": 1,
        "user": doc.user,
        "full_name": doc.full_name,
        "email": doc.email,
        "allowed_warehouses": [w.warehouse for w in doc.get("allowed_warehouses", [])],
        "modules": {
            "CRM": doc.module_crm,
            "BOM": doc.module_bom,
            "Purchase Receipt/GRN": doc.module_pr_grn,
            "Delivery": doc.module_delivery,
            "Packing": doc.module_packing
        },
        "sub_tabs": {
            "CRM": {
                "Opportunities": doc.tab_opportunities,
                "Quotation": doc.tab_quotation,
                "Sales Order": doc.tab_sales_order
            }
        }
    }

