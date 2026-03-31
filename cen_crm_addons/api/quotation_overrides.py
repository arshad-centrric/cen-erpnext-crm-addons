import frappe
from erpnext.crm.doctype.opportunity.opportunity import make_quotation as standard_make_quotation

@frappe.whitelist()
def make_quotation_wrapper(source_name, target_doc=None):
    # 1. Let standard Frappe generate the Quotation mapped doc
    quotation = standard_make_quotation(source_name, target_doc)
    
    # 2. Extract Opportunity
    opp = frappe.get_doc("Opportunity", source_name)
    if opp.opportunity_from == "Lead" and opp.party_name:
        
        # 3. Find Customer by Mobile
        mobile_no = opp.contact_mobile or frappe.db.get_value("Lead", opp.party_name, "mobile_no")
        customer_name = None
        
        if mobile_no:
            customer_name = frappe.db.get_value("Customer", {"mobile_no": mobile_no}, "name")
            
        # 4. Create new Customer if none found
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
                # Fallback to standard flow if auto-creation fails 
                # (e.g. duplicate strict naming series rules)
                frappe.log_error(message=frappe.get_traceback(), title="Customer Auto-Creation Failed")
                return quotation
            
        # 5. Modify the mapped Quotation
        quotation.quotation_to = "Customer"
        quotation.party_name = customer_name
        quotation.customer_name = frappe.db.get_value("Customer", customer_name, "customer_name")
        quotation.contact_person = None 
        quotation.contact_mobile = mobile_no
        quotation.contact_email = frappe.db.get_value("Lead", opp.party_name, "email_id")
        
        # 6. Link Custom Address to this customer if it exists
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
                
    return quotation
