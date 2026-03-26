import frappe

def sync_all_custom_perms():
    frappe.init(site="crm.test")
    frappe.connect()
    
    # 1. Get all doctypes that have at least one Custom DocPerm
    doctypes_with_custom = frappe.get_all("Custom DocPerm", fields=["parent"], distinct=True)
    doctype_names = [d.parent for d in doctypes_with_custom]
    
    print(f"Syncing {len(doctype_names)} doctypes...")
    
    synced_count = 0
    for dt_name in doctype_names:
        try:
            # Get standard permissions from the DocType itself
            dt_doc = frappe.get_doc("DocType", dt_name)
            standard_perms = dt_doc.permissions
            
            for sp in standard_perms:
                # Check if this role already has a Custom DocPerm for this doctype
                if not frappe.db.exists("Custom DocPerm", {"parent": dt_name, "role": sp.role}):
                    # Clone standard perm to custom perm
                    cp = frappe.new_doc("Custom DocPerm")
                    cp.update(sp.as_dict())
                    cp.name = None # Clear name to let it generate
                    cp.doctype = "Custom DocPerm"
                    cp.parent = dt_name
                    cp.insert(ignore_permissions=True)
                    synced_count += 1
        except Exception as e:
            print(f"Error syncing {dt_name}: {e}")
            
    frappe.db.commit()
    print(f"Successfully synced {synced_count} standard permissions into Custom DocPerm!")

if __name__ == "__main__":
    sync_all_custom_perms()
