import json

import frappe
from erpnext.stock.get_item_details import get_item_tax_map

TAX_TEMPLATE_DOCTYPE = "Sales Taxes and Charges Template"

def validate_tax_category(tax_category):
    """Ensures the Tax Category exists and is enabled. Returns its name."""
    tax_category = str(tax_category).strip()
    details = frappe.db.get_value("Tax Category", tax_category, ["name", "disabled"], as_dict=True)
    if not details:
        frappe.throw(f"Tax Category {tax_category} not found")
    if details.disabled:
        frappe.throw(f"Tax Category {tax_category} is disabled")
    return details.name

def validate_company_template(doctype, template, company):
    """Ensures a tax template exists, is enabled and belongs to the Company. Returns its name."""
    template = str(template).strip()
    details = frappe.db.get_value(doctype, template, ["name", "company", "disabled"], as_dict=True)
    if not details:
        frappe.throw(f"{doctype} {template} not found")
    if details.disabled:
        frappe.throw(f"{doctype} {template} is disabled")
    if details.company != company:
        frappe.throw(f"{doctype} {template} belongs to company {details.company}, not {company}")
    return details.name

def apply_quotation_taxes(doc, tax_category=None, taxes_and_charges=None):
    """
    Sets the Tax Category and the Sales Taxes and Charges Template on a new Quotation.
    Without a template, the template of the Company linked to the Tax Category is used.
    """
    if tax_category:
        doc.tax_category = validate_tax_category(tax_category)

    if taxes_and_charges:
        template = validate_company_template(TAX_TEMPLATE_DOCTYPE, taxes_and_charges, doc.company)
    elif tax_category:
        template = frappe.db.get_value(
            TAX_TEMPLATE_DOCTYPE,
            {"company": doc.company, "tax_category": doc.tax_category, "disabled": 0},
            "name",
            order_by="is_default desc"
        )
        if not template:
            frappe.throw(f"No Sales Taxes and Charges Template found for Tax Category {doc.tax_category} in company {doc.company}")
    else:
        return

    # Replace the taxes added from the Company's default template
    doc.taxes_and_charges = template
    doc.set("taxes", [])
    doc.append_taxes_from_master(TAX_TEMPLATE_DOCTYPE)

def validate_applied_item_tax_templates(doc, requested_templates):
    """
    Confirms that ERPNext applied the Item Tax Template requested for each row.
    ERPNext keeps the Item master's template for the Tax Category when they differ,
    so such a request is rejected instead of being silently replaced.
    requested_templates: {row idx: Item Tax Template}
    """
    for row in doc.get("items"):
        template = requested_templates.get(row.idx)
        if not template:
            continue

        expected = get_item_tax_map(doc=doc, tax_template=template, as_json=False)
        applied = json.loads(row.item_tax_rate or "{}")

        if row.item_tax_template != template or applied != expected:
            frappe.throw(
                f"Row #{row.idx} ({row.item_code}): Item Tax Template {template} conflicts with the template "
                f"set on the Item for Tax Category {doc.tax_category or 'blank'}. "
                "Send the Item's template or update the Item master."
            )
