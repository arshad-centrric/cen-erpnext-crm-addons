import frappe
from frappe.utils.pdf import get_pdf
from urllib.parse import urlencode

@frappe.whitelist()
def download_document_pdf(doctype, name, print_format=None):
    """
    Mobile API endpoint for generating PDF documents.
    """
    # 1. PERMISSION CHECK
    frappe.has_permission(doctype, ptype="read", doc=name, throw=True)
    
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


@frappe.whitelist()
def get_print_options(doctype, name):
    """
    Returns a list of configured mobile print formats for the given document, 
    including a ready-to-use download URL for each.
    """
    frappe.has_permission(doctype, ptype="read", doc=name, throw=True)
    
    parentfield_map = {
        "Quotation": "quotation_print_formats",
        "Sales Order": "sales_order_print_formats"
    }
    
    parentfield = parentfield_map.get(doctype)
    if not parentfield:
        frappe.throw(f"Mobile printing is not configured for DocType: {doctype}")

    configs = frappe.get_all(
        "CRM Mobile Print Config",
        filters={"parent": "Cen CRM Settings", "parentfield": parentfield},
        fields=["mobile_label", "is_default", "print_format"]
    )

    base_url = "/api/method/cen_crm_addons.api.mobile_app.print.download_document_pdf"
    options = []
    
    for config in configs:
        params = urlencode({
            "doctype": doctype,
            "name": name,
            "print_format": config.print_format
        })
        
        options.append({
            "label": config.mobile_label,
            "is_default": config.is_default,
            "download_url": f"{base_url}?{params}"
        })
        
    return options
