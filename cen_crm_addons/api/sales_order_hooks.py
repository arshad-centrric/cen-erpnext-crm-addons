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

    opp_doc = frappe.get_doc("Opportunity", opportunity_id)

    # Pass the Box ID from Opportunity to Quotation
    if opp_doc.get("custom_box_id"):
        doc.custom_box_id = opp_doc.custom_box_id

    # Map Delivery Locations child table
    if opp_doc.get("custom_location_details"):
        doc.set("custom_location_details", [])
        has_courier = False
        
        for row in opp_doc.custom_location_details:
            new_row = doc.append("custom_location_details", {})
            for fieldname in [
                "delivery_label", "custom_delivery_store", "custom_mode_of_delivery", 
                "custom_delivery_partner", "custom_delivery_date", "custom_delivery_time", 
                "custom_address_line_1", "custom_address_line_2", "custom_delivery_city", 
                "custom_delivery_state", "custom_pincode", "custom_delivery_country",
                "custom_delivery_contact"
            ]:
                new_row.set(fieldname, row.get(fieldname))
                
            if row.get("custom_mode_of_delivery") == "Courier":
                has_courier = True

        # Auto-append delivery charge item if mapped to Courier
        if has_courier:
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
        
    quotation = frappe.get_doc("Quotation", quotation_id)
    
    if quotation.get("custom_box_id"):
        doc.custom_box_id = quotation.custom_box_id
        
    locations = quotation.get("custom_location_details", [])
    
    if locations:
        target_row = locations[0]
        
        fields_to_copy = [
            "custom_mode_of_delivery", "custom_delivery_partner", "custom_delivery_store", 
            "custom_delivery_date", "custom_delivery_time", "custom_address_line_1", 
            "custom_address_line_2", "custom_delivery_city", "custom_delivery_state", 
            "custom_pincode", "custom_delivery_country", "custom_delivery_contact"
        ]
        
        for field in fields_to_copy:
            if target_row.get(field):
                doc.set(field, target_row.get(field))
                
        if target_row.get("custom_delivery_date"):
            doc.delivery_date = target_row.get("custom_delivery_date")
            for item in doc.items:
                item.delivery_date = target_row.get("custom_delivery_date")
                
        delivery_store = target_row.get("custom_delivery_store")
        if not delivery_store:
            delivery_store = frappe.db.get_single_value("Stock Settings", "default_warehouse")
            
        if delivery_store:
            doc.set_warehouse = delivery_store
            for item in doc.items:
                item.warehouse = delivery_store

@frappe.whitelist()
def get_linked_sales_orders(quotation_name):
    """Securely fetches unique Sales Orders linked to a Quotation, bypassing child table API permission errors."""
    sales_orders = frappe.db.sql("""
        SELECT DISTINCT parent 
        FROM `tabSales Order Item` 
        WHERE prevdoc_docname = %s 
        AND docstatus < 2
    """, quotation_name, as_dict=True)
    
    return [so.parent for so in sales_orders]

@frappe.whitelist()
def make_sales_order_wrapper(source_name, target_doc=None, args=None):
    from erpnext.selling.doctype.quotation.quotation import make_sales_order
    doc = make_sales_order(source_name, target_doc, args=args)
    _apply_quotation_mapping_to_sales_order(doc, source_name=source_name)
    return doc

@frappe.whitelist()
def make_split_sales_order(source_name, payload=None):
    if not payload:
        args = getattr(frappe.flags, "args", {})
        payload = args.get("payload", {})
        
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
        
    target_address_row_name = payload.get("target_address_row_name")
    items_payload = payload.get("items", [])
    
    quotation = frappe.get_doc("Quotation", source_name)
    target_row = next((row for row in quotation.get("custom_location_details", []) if row.name == target_address_row_name), None)
    
    if not target_row:
        frappe.throw("Selected delivery address row not found in Quotation.")
        
    from erpnext.selling.doctype.quotation.quotation import make_sales_order
    mapped_so = make_sales_order(source_name)
    
    if quotation.get("custom_box_id"):
        mapped_so.custom_box_id = quotation.custom_box_id
    
    original_items = mapped_so.get("items")
    mapped_so.set("items", [])
    
    payload_item_map = {p.get("quotation_item_name"): p.get("allocate_qty") for p in items_payload}
    
    for item in original_items:
        if item.quotation_item in payload_item_map:
            item.qty = payload_item_map[item.quotation_item]
            mapped_so.append("items", item)
            
    if not mapped_so.get("items"):
        frappe.throw("No valid items allocated for this Sales Order.")
        
    fields_to_copy = [
        "custom_mode_of_delivery", "custom_delivery_partner", "custom_delivery_store", 
        "custom_delivery_date", "custom_delivery_time", "custom_address_line_1", 
        "custom_address_line_2", "custom_delivery_city", "custom_delivery_state", 
        "custom_pincode", "custom_delivery_country", "custom_delivery_contact"
    ]
    
    for field in fields_to_copy:
        mapped_so.set(field, target_row.get(field))
        
    if target_row.get("custom_delivery_date"):
        mapped_so.delivery_date = target_row.get("custom_delivery_date")
        for item in mapped_so.items:
            item.delivery_date = target_row.get("custom_delivery_date")
            
    delivery_store = target_row.get("custom_delivery_store")
    if not delivery_store:
        # Fallback to default stock settings to scrub any disabled warehouses from the old quotation
        delivery_store = frappe.db.get_single_value("Stock Settings", "default_warehouse")
        
    if delivery_store:
        mapped_so.set_warehouse = delivery_store
        for item in mapped_so.items:
            item.warehouse = delivery_store

    return mapped_so

@frappe.whitelist()
def get_consolidated_payment_entry_data(source_name, target_doc=None):
    from frappe.utils import flt
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    
    # 1. Fetch Quotations linked to the Opportunity
    quotations = frappe.get_all("Quotation", filters={"opportunity": source_name}, pluck="name")
    if not quotations:
        frappe.throw("No active, unpaid Sales Orders found for this Opportunity. They may already be fully paid.")
        
    # 2. Fetch Sales Orders linked to these Quotations via items table
    so_items = frappe.get_all(
        "Sales Order Item",
        filters={"prevdoc_docname": ("in", quotations)},
        pluck="parent"
    )
    if not so_items:
        frappe.throw("No active, unpaid Sales Orders found for this Opportunity. They may already be fully paid.")
        
    so_names = list(set(so_items))
    
    sales_orders = frappe.get_all(
        "Sales Order",
        filters={"name": ("in", so_names), "docstatus": 1},
        fields=["name", "grand_total", "advance_paid", "customer"]
    )
    
    valid_sos = []
    for so in sales_orders:
        outstanding = flt(so.grand_total) - flt(so.advance_paid)
        if outstanding > 0:
            valid_sos.append({"name": so.name, "outstanding": outstanding, "customer": so.customer})
            
    if not valid_sos:
        frappe.throw("No active, unpaid Sales Orders found for this Opportunity. They may already be fully paid.")
        
    # Generate the base Payment Entry using the FIRST valid Sales Order
    base_so = valid_sos[0]
    pe_doc = get_payment_entry("Sales Order", base_so["name"])
    
    # We already have the first SO in pe_doc.references. Let's add the rest.
    total_amount = flt(pe_doc.paid_amount)
    
    for so in valid_sos[1:]:
        pe_doc.append("references", {
            "reference_doctype": "Sales Order",
            "reference_name": so["name"],
            "total_amount": flt(so["outstanding"]),
            "outstanding_amount": flt(so["outstanding"]),
            "allocated_amount": flt(so["outstanding"])
        })
        total_amount += flt(so["outstanding"])
        
    pe_doc.paid_amount = total_amount
    pe_doc.received_amount = total_amount
    
    # Map Box ID from Opportunity
    box_id = frappe.db.get_value("Opportunity", source_name, "custom_box_id")
    if box_id:
        pe_doc.custom_box_id = box_id
    
    return pe_doc
