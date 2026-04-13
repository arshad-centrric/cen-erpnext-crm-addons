import frappe

def sync_user_permissions(doc, method):
    """
    Hook tied to on_update of User Payment Mapping.
    Flushes and recreates standard ERPNext User Permissions.
    """
    user = doc.user
    
    # 1. Clear existing Mode of Payment restrictions for this user
    existing_perms = frappe.get_all("User Permission", filters={
        "user": user,
        "allow": "Mode of Payment"
    })
    
    for perm in existing_perms:
        frappe.delete_doc("User Permission", perm.name, force=True, ignore_permissions=True)
        
    # 2. Re-create new restrictions from the child table
    for item in doc.get("allowed_modes"):
        mop = item.mode_of_payment
        if mop:
            # Recreate permission record
            new_perm = frappe.new_doc("User Permission")
            new_perm.user = user
            new_perm.allow = "Mode of Payment"
            new_perm.for_value = mop
            new_perm.apply_to_all_doctypes = 1
            new_perm.insert(ignore_permissions=True)

def remove_user_permissions(doc, method):
    """
    Hook tied to on_trash of User Payment Mapping.
    """
    user = doc.user
    existing_perms = frappe.get_all("User Permission", filters={
        "user": user,
        "allow": "Mode of Payment"
    })
    for perm in existing_perms:
        frappe.delete_doc("User Permission", perm.name, force=True, ignore_permissions=True)
