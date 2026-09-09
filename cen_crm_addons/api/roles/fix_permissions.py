import frappe

def fix_permissions():
    roles_to_clean = ["AGT - POS User", "AGT - Packing User", "AGT - Delivery User", "AGT - Purchase User"]
    
    # 1. Delete all our faulty custom permissions to restore standard baseline
    for role in roles_to_clean:
        frappe.db.delete("Custom DocPerm", {"role": role})
        print(f"Cleared faulty permissions for {role}")
    
    frappe.db.commit()
    frappe.clear_cache()
    
    # 2. Re-run all 4 setup scripts using the NEW logic!
    from cen_crm_addons.api.roles.pos_user import setup_pos_operator_role
    from cen_crm_addons.api.roles.pack_user import setup_pack_user_role
    from cen_crm_addons.api.roles.delivery_user import setup_delivery_user_role
    from cen_crm_addons.api.roles.purchase_user import setup_purchase_user_role
    
    print("Re-applying POS permissions safely...")
    setup_pos_operator_role()
    
    print("Re-applying Pack permissions safely...")
    setup_pack_user_role()
    
    print("Re-applying Delivery permissions safely...")
    setup_delivery_user_role()
    
    print("Re-applying Purchase permissions safely...")
    setup_purchase_user_role()
    
    print("Permissions have been fully restored and safely applied!")

