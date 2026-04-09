import frappe

def _apply_opportunity_mapping(doc, source_name=None):
    """
    Internal helper to perform the actual cross-doc data mapping.
    """
    quotation_id = source_name

    # Fallback to items if source_name wasn't explicitly passed (e.g., from before_validate)
    if not quotation_id:
        if not doc.items:
            return

        for item in doc.items:
            # Frappe mapper doesn't always explicitly set prevdoc_doctype until save.
            has_qtn_link = item.get("prevdoc_docname") or item.get("quotation_item")
            if has_qtn_link:
                # We can trace it via prevdoc_docname which holds the quotation ID
                if item.get("prevdoc_docname"):
                    quotation_id = item.get("prevdoc_docname")
                    break
    
    if not quotation_id:
        return

    # 2. Find the Opportunity linked to that Quotation
    opportunity_id = frappe.db.get_value("Quotation", quotation_id, "opportunity")
    if not opportunity_id:
        return

    # 3. Fetch custom fields from the Opportunity
    opp_data = frappe.db.get_value(
        "Opportunity", 
        opportunity_id, 
        ["custom_delivery_date", "custom_delivery_store"], 
        as_dict=1
    )

    if not opp_data:
        return

    # 4. Map data if target fields are blank
    if opp_data.custom_delivery_date and not doc.delivery_date:
        doc.delivery_date = opp_data.custom_delivery_date
    
    if opp_data.custom_delivery_store and not doc.set_warehouse:
        doc.set_warehouse = opp_data.custom_delivery_store
        
    # 5. Push delivery_date to child items
    if doc.delivery_date:
        for item in doc.items:
            item.delivery_date = doc.delivery_date

@frappe.whitelist()
def make_sales_order_wrapper(source_name, target_doc=None, args=None):
    """
    Wraps the standard ERPNext mapper to ensure Opportunity data is 
    included in the document object BEFORE it is sent to the UI.
    """
    from erpnext.selling.doctype.quotation.quotation import make_sales_order
    
    # Call standard mapper
    doc = make_sales_order(source_name, target_doc, args=args)
    
    # Manually apply our additional mappings
    _apply_opportunity_mapping(doc, source_name=source_name)
    
    return doc

