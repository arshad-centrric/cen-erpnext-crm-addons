import frappe

@frappe.whitelist()
def search_customers_by_phone(txt):
    if not txt:
        return []

    # Search for exactly matching or partially matching mobile_no in Customer
    query = """
        SELECT name, customer_name, mobile_no 
        FROM `tabCustomer` 
        WHERE mobile_no LIKE %s
        LIMIT 20
    """
    
    wildcard_txt = f"%{txt}%"
    return frappe.db.sql(query, (wildcard_txt,), as_dict=True)

@frappe.whitelist()
def get_opportunity_history_by_phone(mobile_no):
    if not mobile_no:
        return []
        
    query = """
        SELECT name, status, creation, custom_assigned_full_name, custom_assigned_to
        FROM `tabOpportunity`
        WHERE contact_mobile = %s
        ORDER BY creation DESC
    """
    
    return frappe.db.sql(query, (mobile_no,), as_dict=True)
