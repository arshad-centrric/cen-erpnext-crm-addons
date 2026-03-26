import frappe

def fix():
    frappe.init(site="crm.test")
    frappe.connect()
    
    if not frappe.db.exists("Role", "Sales Person"):
        doc = frappe.new_doc("Role")
        doc.role_name = "Sales Person"
        doc.desk_access = 1
        doc.insert(ignore_permissions=True)
        
    doc = frappe.get_doc("Role Profile", "CRM Sales Person")
    doc.set("roles", [])
    doc.append("roles", {"role": "Sales Person"})
    doc.save(ignore_permissions=True)
    
    for email in ["sales1@test.com", "sales2@test.com"]:
        user = frappe.get_doc("User", email)
        user.add_roles("Sales Person")
        user.save(ignore_permissions=True)
        
    frappe.db.commit()
    print("Fixed roles")

fix()
