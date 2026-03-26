import frappe

def create_role(name):
    if not frappe.db.exists("Role", name):
        doc = frappe.new_doc("Role")
        doc.role_name = name
        doc.desk_access = 1
        doc.insert(ignore_permissions=True)
        print(f"Created Role: {name}")

def create_role_profile(name, roles):
    if not frappe.db.exists("Role Profile", name):
        doc = frappe.new_doc("Role Profile")
        doc.role_profile = name
        for role in roles:
            # Ensure the role actually exists
            if frappe.db.exists("Role", role):
                doc.append("roles", {"role": role})

        doc.insert(ignore_permissions=True)
        print(f"Created Role Profile: {name}")
    else:
        print(f"Role Profile {name} already exists.")

def create_user(email, first_name, profile):
    if not frappe.db.exists("User", email):
        doc = frappe.new_doc("User")
        doc.email = email
        doc.first_name = first_name
        doc.send_welcome_email = 0
        doc.role_profile_name = profile
        doc.insert(ignore_permissions=True)
        # Set a default password
        doc.add_roles(*[r.role for r in frappe.get_doc("Role Profile", profile).roles])
        
        # update password
        from frappe.utils.password import update_password
        update_password(email, "Test@123")
        
        print(f"Created User: {email} with password 'Test@123'")
    else:
        print(f"User {email} already exists.")

def create_lead(lead_name, company_name, owner=None):
    # check if exist by company Name
    if not frappe.db.exists("Lead", {"company_name": company_name}):
        doc = frappe.new_doc("Lead")
        doc.lead_name = lead_name
        doc.company_name = company_name
        if owner:
            doc.lead_owner = owner
        doc.insert(ignore_permissions=True)
        print(f"Created Lead: {lead_name} (Assigned to: {owner or 'Unassigned'})")
    else:
        print(f"Lead {company_name} already exists.")

def setup():
    frappe.init(site="crm.test")
    frappe.connect()
    
    # 0. Create custom roles
    create_role("Sales Person")
    
    # 1. Create Role Profiles
    create_role_profile("CRM Supervisor", ["Sales Manager", "System Manager", "Item Manager", "Sales Master Manager"])
    create_role_profile("CRM Sales Person", ["Sales Person", "Item Viewer", "Sales User"])

    
    # 2. Create standard users
    create_user("supervisor@test.com", "Super", "CRM Supervisor")
    create_user("sales1@test.com", "Sales One", "CRM Sales Person")
    create_user("sales2@test.com", "Sales Two", "CRM Sales Person")
    
    # 3. Create test leads
    create_lead("Test Lead Alpha", "Alpha Solutions", owner="sales1@test.com")
    create_lead("Test Lead Beta", "Beta Corp", owner="sales2@test.com")
    create_lead("Test Lead Gamma", "Gamma Systems", owner=None)  # Unassigned lead
    
    frappe.db.commit()
    print("\\n=== Setup Complete ===")
    print("Testing instructions:")
    print("1. Login as supervisor@test.com (Password: Test@123). You should see all 3 Leads.")
    print("2. Login as sales1@test.com (Password: Test@123). You should ONLY see Alpha Solutions.")
    
if __name__ == "__main__":
    setup()

def update_crm_sales_person():
    frappe.init(site="crm.test")
    frappe.connect()
    try:
        doc = frappe.get_doc("Role Profile", "CRM Sales Person")
        doc.set("roles", [])
        for r in ["Sales Person", "Item Viewer"]:
            doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Updated CRM Sales Person role profile to include 'Sales Person'")
        
        # update existing users
        for email in ["sales1@test.com", "sales2@test.com"]:
            user = frappe.get_doc("User", email)
            user.add_roles(*[r.role for r in doc.roles])
            user.save(ignore_permissions=True)
            print(f"Updated roles for {email}")
        frappe.db.commit()
    except Exception as e:
        print(f"Error: {e}")
