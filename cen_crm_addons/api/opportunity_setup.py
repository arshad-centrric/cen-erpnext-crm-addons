import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def setup_opportunity_statuses():
    """
    Updates the Opportunity status options to match the client's sales workflow.
    Ensures correct order and preserves existing standard statuses.
    """
    
    statuses = [
        "Open",
        "Replied",
        "To be quoted",
        "Quotation",
        "Quotation Send",
        "Revise the Quote",
        "Converted",
        "Packed",
        "Delivered",
        "To be paid",
        "Closed",
        "Lost"
    ]
    
    options = "\n".join(statuses)
    
    # Update Status field options
    make_property_setter(
        doctype="Opportunity",
        fieldname="status",
        property="options",
        value=options,
        property_type="Text"
    )
    
    # Ensure default is set to Open
    make_property_setter(
        doctype="Opportunity",
        fieldname="status",
        property="default",
        value="Open",
        property_type="Text"
    )
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Opportunity")
