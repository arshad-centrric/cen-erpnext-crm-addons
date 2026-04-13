import frappe

def _apply_opportunity_mapping_to_quotation(doc, source_name=None):
    """Maps custom delivery fields from Opportunity to Quotation."""
    opportunity_id = source_name or doc.opportunity
    if not opportunity_id:
        return

    # Fetch all 5 fields
    opp_data = frappe.db.get_value(
        "Opportunity", 
        opportunity_id, 
        ["custom_delivery_partner", "custom_mode_of_delivery", "custom_delivery_time", "custom_delivery_store", "custom_delivery_date"], 
        as_dict=1
    )

    if not opp_data:
        return

    # Map only if target fields are blank
    if opp_data.custom_delivery_partner and not doc.custom_delivery_partner:
        doc.custom_delivery_partner = opp_data.custom_delivery_partner

    if opp_data.custom_mode_of_delivery and not doc.custom_mode_of_delivery:
        doc.custom_mode_of_delivery = opp_data.custom_mode_of_delivery

    if opp_data.custom_delivery_time and not doc.custom_delivery_time:
        doc.custom_delivery_time = opp_data.custom_delivery_time
        
    if opp_data.custom_delivery_store and not doc.custom_delivery_store:
        doc.custom_delivery_store = opp_data.custom_delivery_store
        
    if opp_data.custom_delivery_date and not doc.custom_delivery_date:
        doc.custom_delivery_date = opp_data.custom_delivery_date

    # Auto-append delivery charge item if mapped to Courier
    if getattr(doc, "custom_mode_of_delivery", None) == "Courier":
        delivery_item = frappe.db.get_single_value("Cen CRM Settings", "delivery_charge_item")
        if delivery_item:
            # Prevent appending identical delivery line if someone refreshes somehow
            existing_items = [d.item_code for d in doc.items] if hasattr(doc, "items") and doc.items else []
            if delivery_item not in existing_items:
                item_details = frappe.db.get_value("Item", delivery_item, ["item_name", "description", "stock_uom"], as_dict=1)
                if item_details:
                    doc.append("items", {
                        "item_code": delivery_item,
                        "item_name": item_details.item_name,
                        "description": item_details.description,
                        "qty": 1,
                        "uom": item_details.stock_uom
                    })

@frappe.whitelist()
def make_quotation_wrapper(source_name, target_doc=None, args=None):
    """Wraps doc mapping to ensure fields are populated BEFORE saving in the UI."""
    from erpnext.crm.doctype.opportunity.opportunity import make_quotation
    doc = make_quotation(source_name, target_doc)
    _apply_opportunity_mapping_to_quotation(doc, source_name)
    return doc

def _apply_quotation_mapping_to_sales_order(doc, source_name=None):
    """Maps custom delivery fields from Quotation to Sales Order."""
    quotation_id = source_name
    
    # Fallback to items if source_name wasn't explicitly passed
    if not quotation_id:
        if not doc.items:
            return
        for item in doc.items:
            has_qtn_link = item.get("prevdoc_docname") or item.get("quotation_item")
            if has_qtn_link:
                if item.get("prevdoc_docname"):
                    quotation_id = item.get("prevdoc_docname")
                    break

    if not quotation_id:
        return
        
    qtn_data = frappe.db.get_value(
        "Quotation", 
        quotation_id, 
        ["custom_delivery_partner", "custom_mode_of_delivery", "custom_delivery_time", "opportunity"], 
        as_dict=1
    )
    
    if not qtn_data:
        return
        
    # Map Quotation fields to Sales Order
    if qtn_data.get("custom_delivery_partner") and not doc.custom_delivery_partner:
        doc.custom_delivery_partner = qtn_data.custom_delivery_partner
        
    if qtn_data.get("custom_mode_of_delivery") and not doc.custom_mode_of_delivery:
        doc.custom_mode_of_delivery = qtn_data.custom_mode_of_delivery
        
    if qtn_data.get("custom_delivery_time") and not doc.custom_delivery_time:
        doc.custom_delivery_time = qtn_data.custom_delivery_time

    # Map Store and Date directly via the linked Opportunity logic
    opportunity_id = qtn_data.opportunity
    if not opportunity_id:
        return

    opp_data = frappe.db.get_value(
        "Opportunity", 
        opportunity_id, 
        ["custom_delivery_date", "custom_delivery_store"], 
        as_dict=1
    )

    if not opp_data:
        return

    if opp_data.custom_delivery_date and not doc.delivery_date:
        doc.delivery_date = opp_data.custom_delivery_date
    
    if opp_data.custom_delivery_store and not doc.set_warehouse:
        doc.set_warehouse = opp_data.custom_delivery_store
        
    # Push delivery_date to child items
    if doc.delivery_date:
        for item in doc.items:
            item.delivery_date = doc.delivery_date

@frappe.whitelist()
def make_sales_order_wrapper(source_name, target_doc=None, args=None):
    from erpnext.selling.doctype.quotation.quotation import make_sales_order
    doc = make_sales_order(source_name, target_doc, args=args)
    _apply_quotation_mapping_to_sales_order(doc, source_name=source_name)
    return doc
