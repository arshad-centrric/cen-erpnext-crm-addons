import frappe
def run():
    frappe.init(site="crm.test")
    frappe.connect()
    doc = frappe.get_doc("Role Profile", "CRM Sales Person")
    has_sales_user = any(r.role == "Sales User" for r in doc.roles)
    if not has_sales_user:
        doc.append("roles", {"role": "Sales User"})
        doc.save(ignore_permissions=True)
    
    for email in ["sales1@test.com", "sales2@test.com"]:
        user = frappe.get_doc("User", email)
        user.add_roles("Sales User")
        user.save(ignore_permissions=True)
    frappe.db.commit()
    print("Fixed roles by adding Sales User")
