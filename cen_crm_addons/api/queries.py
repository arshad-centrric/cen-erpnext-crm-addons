import frappe

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_sales_persons(doctype, txt, searchfield, start, page_len, filters):
    # SQL query to fetch only active users who have the 'Sales Person' role
    return frappe.db.sql("""
        SELECT name, full_name
        FROM `tabUser`
        WHERE enabled = 1 
        AND name IN (
            SELECT parent FROM `tabHas Role` WHERE role = 'Sales Person'
        )
        AND (name LIKE %(txt)s OR full_name LIKE %(txt)s)
        ORDER BY full_name ASC
        LIMIT %(start)s, %(page_len)s
    """, {
        'txt': f"%{txt}%",
        'start': start,
        'page_len': page_len
    })