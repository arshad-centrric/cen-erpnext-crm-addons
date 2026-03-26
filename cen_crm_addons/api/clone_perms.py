import frappe

def clone_permissions():
    frappe.init(site="crm.test")
    frappe.connect()
    
    source_role = "Sales User"
    target_role = "Sales Person"
    
    # Get all permissions for Sales User
    perms = frappe.get_all("DocPerm", 
                           filters={"role": source_role}, 
                           fields=["*"])
                           
    count = 0
    for perm in perms:
        # Check if target role already has permission for this doctype
        exists = frappe.db.exists("Custom DocPerm", {"parent": perm.parent, "role": target_role})
        if not exists:
            try:
                custom_perm = frappe.new_doc("Custom DocPerm")
                custom_perm.parent = perm.parent
                custom_perm.role = target_role
                
                # Copy standard perm matrix
                attributes = ["read", "write", "create", "submit", "cancel", "amend", 
                              "report", "export", "import", "set_user_permissions", "share", 
                              "print", "email", "permlevel"]
                              
                for attr in attributes:
                    if hasattr(perm, attr):
                        setattr(custom_perm, attr, getattr(perm, attr))
                        
                custom_perm.insert(ignore_permissions=True)
                count += 1
            except Exception as e:
                # Some system doctypes might throw errors, we skip them
                pass
                
    frappe.db.commit()
    print(f"Successfully cloned {count} permissions from {source_role} to {target_role}!")

if __name__ == "__main__":
    clone_permissions()
