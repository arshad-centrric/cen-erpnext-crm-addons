import frappe
from frappe.utils.pdf import get_pdf
from urllib.parse import urlencode

@frappe.whitelist(allow_guest=True)
def download_document_pdf(doctype, name, print_format=None):
    """
    Mobile API endpoint for generating PDF documents.
    """
    frappe.flags.ignore_permissions = True
    
    # 2. DYNAMIC CONFIG LOOKUP
    if not print_format:
        parentfield_map = {
            "Quotation": "quotation_print_formats",
            "Sales Order": "sales_order_print_formats"
        }
        
        parentfield = parentfield_map.get(doctype)
        if not parentfield:
            frappe.throw(f"Mobile printing is not configured for DocType: {doctype}")
            
        print_format = frappe.db.get_value(
            "CRM Mobile Print Config", 
            {"parent": "Cen CRM Settings", "parentfield": parentfield, "is_default": 1}, 
            "print_format"
        )
        
        if not print_format:
            frappe.throw(f"No default mobile print format configured for {doctype} in Cen CRM Settings.", exc=frappe.ValidationError)

    # 3. GENERATION
    html = frappe.get_print(doctype, name, print_format)
    
    # 4. CONVERSION
    pdf_content = get_pdf(html)
    
    # 5. RESPONSE HIJACK
    frappe.response.filename = f"{name}.pdf"
    frappe.response.filecontent = pdf_content
    frappe.response.type = "download"


# @frappe.whitelist()
# def get_print_options(doctype, name):
#     """
#     Returns a list of configured mobile print formats for the given document, 
#     including a ready-to-use download URL for each.
#     """
#     frappe.has_permission(doctype, ptype="read", doc=name, throw=True)
    
#     parentfield_map = {
#         "Quotation": "quotation_print_formats",
#         "Sales Order": "sales_order_print_formats"
#     }
    
#     parentfield = parentfield_map.get(doctype)
#     if not parentfield:
#         frappe.throw(f"Mobile printing is not configured for DocType: {doctype}")

#     configs = frappe.get_all(
#         "CRM Mobile Print Config",
#         filters={"parent": "Cen CRM Settings", "parentfield": parentfield},
#         fields=["mobile_label", "is_default", "print_format"]
#     )

#     base_url = "/api/method/cen_crm_addons.api.mobile_app.print.download_document_pdf"
#     options = []
    
#     for config in configs:
#         params = urlencode({
#             "doctype": doctype,
#             "name": name,
#             "print_format": config.print_format
#         })
        
#         options.append({
#             "label": config.mobile_label,
#             "is_default": config.is_default,
#             "download_url": f"{base_url}?{params}"
#         })
        
#     return options


@frappe.whitelist()
def get_print_options(doctype, name):
    """
    Returns a list of configured mobile print formats for the given document or tab, 
    including a ready-to-use download URL for each.
    """
    # 1. Map the incoming 'doctype' string to the correct Settings child table
    parentfield_map = {
        "Quotation": "quotation_print_formats",
        "Sales Order": "sales_order_print_formats",
        "Packing": "packing_print_formats",         # Pseudo-doctype for mobile tabs
        "Delivery": "delivery_note_print_formats",  # Pseudo-doctype for mobile tabs
        "Purchase Receipt": "purchase_receipt_print_formats",
        "Sales Invoice": "sales_invoice_print_formats"
    }
    
    parentfield = parentfield_map.get(doctype)
    if not parentfield:
        frappe.throw(f"Mobile printing is not configured for: {doctype}")

    # 2. Resolve the actual Frappe DocType for permissions and PDF generation
    actual_doctype = doctype
    if doctype in ["Packing", "Delivery"]:
        actual_doctype = "Sales Order"

    # 3. Permission Check (using the actual DocType, e.g., 'Sales Order')
    frappe.has_permission(actual_doctype, ptype="read", doc=name, throw=True)
    
    # 4. Fetch Print Configurations
    configs = frappe.get_all(
        "CRM Mobile Print Config",
        filters={"parent": "Cen CRM Settings", "parentfield": parentfield},
        fields=["mobile_label", "is_default", "print_format"]
    )

    # 5. Generate Download URLs using the new directory structure path
    base_url = "/api/method/cen_crm_addons.mobile_api.print.download_document_pdf"
    options = []
    
    for config in configs:
        params = urlencode({
            "doctype": actual_doctype,  # Pass the real DocType to the PDF generator API
            "name": name,
            "print_format": config.print_format
        })
        
        options.append({
            "label": config.mobile_label,
            "is_default": config.is_default,
            "download_url": f"{base_url}?{params}"
        })
        
    return options

@frappe.whitelist()
def get_public_share_link(doctype, name):
    secret_key = frappe.get_doc(doctype, name).get_signature()
    base_url = "/api/method/cen_crm_addons.mobile_api.print.download_public_pdf"
    params = urlencode({
        "doctype": doctype,
        "name": name,
        "key": secret_key
    })
    
    long_url = f"{base_url}?{params}"
    
    short_link = frappe.new_doc("Short Link")
    short_link.url = long_url
    short_link.insert(ignore_permissions=True)
    frappe.db.commit() # Ensure it is saved
    
    tiny_url = f"/s/{short_link.name}"
    
    return {"public_download_url": tiny_url}

@frappe.whitelist(allow_guest=True)
def download_public_pdf(doctype, name, key, print_format=None):
    if not key:
        raise frappe.PermissionError("Not permitted")
        
    parentfield_map = {
        "Quotation": "quotation_print_formats",
        "Sales Order": "sales_order_print_formats",
        "Packing": "packing_print_formats",
        "Delivery": "delivery_note_print_formats",
        "Purchase Receipt": "purchase_receipt_print_formats",
        "Sales Invoice": "sales_invoice_print_formats"
    }
    
    parentfield = parentfield_map.get(doctype)
    if not parentfield:
        frappe.throw(f"Mobile printing is not configured for: {doctype}", exc=frappe.ValidationError)

    actual_doctype = doctype
    if doctype in ["Packing", "Delivery"]:
        actual_doctype = "Sales Order"

    if not print_format:
        print_format = frappe.db.get_value(
            "CRM Mobile Print Config",
            {"parent": "Cen CRM Settings", "parentfield": parentfield, "is_default": 1},
            "print_format"
        )
        if not print_format:
            frappe.throw(f"No default mobile print format configured for {doctype} in Cen CRM Settings.", exc=frappe.ValidationError)
        
    frappe.flags.ignore_permissions = True
    doc = frappe.get_doc(actual_doctype, name)
    
    if doc.get_signature() != key:
        raise frappe.PermissionError("Not permitted")
        
    original_user = frappe.session.user
    frappe.session.user = "Administrator"
    
    try:
        html = frappe.get_print(actual_doctype, name, print_format)
        pdf_content = get_pdf(html)
        
        frappe.response.filename = f"{name}.pdf"
        frappe.response.filecontent = pdf_content
        frappe.response.type = "download"
    finally:
        frappe.session.user = original_user