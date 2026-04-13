import frappe

def setup_picking_profile():
    """
    Creates the Role Profile specifically for Picking Users.
    """
    create_role_profile()

def create_role_profile():
    profile_name = "CRM Picking User"
    
    if not frappe.db.exists("Role Profile", profile_name):
        doc = frappe.new_doc("Role Profile")
        doc.role_profile = profile_name
        doc.append("roles", {"role": "Picking User"})
        doc.append("roles", {"role": "Desk User"})
        # We do NOT add Workspace Manager, so they only see explicitly allowed Workspaces.
        doc.insert(ignore_permissions=True)
        frappe.db.commit()


