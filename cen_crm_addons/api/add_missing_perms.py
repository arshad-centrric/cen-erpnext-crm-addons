import frappe

def add_missing_perms():
    frappe.init(site="crm.test")
    frappe.connect()
    
    target_role = "Sales Person"
    missing_doctypes = ["Sales Stage", "Opportunity Type", "Lead Source"]
    
    for dt in missing_doctypes:
        # Check if already exists
        if not frappe.db.exists("Custom DocPerm", {"parent": dt, "role": target_role}):
            try:
                custom_perm = frappe.new_doc("Custom DocPerm")
                custom_perm.parent = dt
                custom_perm.role = target_role
                custom_perm.read = 1
                custom_perm.insert(ignore_permissions=True)
                print(f"Granted Read to {dt}")
            except Exception as e:
                pass
                
    frappe.db.commit()
    print("Done adding missing permissions.")

if __name__ == "__main__":
    add_missing_perms()
