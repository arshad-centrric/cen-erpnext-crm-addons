import frappe

def _apply_customer_auto_creation(quotation, source_name):
    """Finds or auto-creates a Customer by mobile when Quoting from a Lead."""
    opp = frappe.get_doc("Opportunity", source_name)
    
    # Only process if this Opportunity originated directly from a Lead
    if opp.opportunity_from == "Lead" and opp.party_name:
        mobile_no = opp.contact_mobile or frappe.db.get_value("Lead", opp.party_name, "mobile_no")
        customer_name = None
        
        if mobile_no:
            customer_name = frappe.db.get_value("Customer", {"mobile_no": mobile_no}, "name")
            
        if not customer_name:
            lead = frappe.get_doc("Lead", opp.party_name)
            customer = frappe.new_doc("Customer")
            customer.customer_name = lead.lead_name or lead.company_name or opp.party_name
            customer.customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or "Commercial"
            customer.territory = lead.territory or frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
            customer.lead_name = lead.name
            customer.opportunity_name = opp.name
            if mobile_no:
                customer.mobile_no = mobile_no
            try:
                customer.insert(ignore_permissions=True)
                customer_name = customer.name
            except Exception as e:
                frappe.log_error(message=frappe.get_traceback(), title="Customer Auto-Creation Failed")
                return # Fail gracefully and fallback to standard
                
        # Link mapped quotation to the true customer
        quotation.quotation_to = "Customer"
        quotation.party_name = customer_name
        quotation.customer_name = frappe.db.get_value("Customer", customer_name, "customer_name")
        quotation.contact_person = None 
        quotation.contact_mobile = mobile_no
        quotation.contact_email = frappe.db.get_value("Lead", opp.party_name, "email_id")
        
        # Link Custom Address from Opportunity to the selected/new Customer
        address_name = frappe.db.get_value("Dynamic Link", {
            "link_doctype": "Opportunity",
            "link_name": opp.name,
            "parenttype": "Address"
        }, "parent")
        
        if address_name:
            address = frappe.get_doc("Address", address_name)
            is_linked = any(link.link_doctype == "Customer" and link.link_name == customer_name for link in address.links)
            
            if not is_linked:
                address.append("links", {
                    "link_doctype": "Customer",
                    "link_name": customer_name
                })
                address.save(ignore_permissions=True)

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
    
    # 1. Customer Auto-Creation (if originated from Lead)
    _apply_customer_auto_creation(doc, source_name)
    
    # 2. Logistics & Delivery Automation
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
