import frappe

def generate_box_id(doc, method):
    """Generates a sequential Box ID for Opportunities using Cen CRM Settings."""
    if doc.get("custom_box_id"):
        return

    # Phase 2: Relational Store-Wise logic
    user = frappe.session.user
    
    # 1. Query User Permission to find the strictly allowed Warehouse
    permitted_warehouses = frappe.get_all(
        "User Permission",
        filters={"user": user, "allow": "Warehouse"},
        fields=["for_value"]
    )
    
    if not permitted_warehouses:
        frappe.throw(f"Cannot generate Box ID: No Warehouse permission found for user {user}.")
    elif len(permitted_warehouses) > 1:
        frappe.throw(f"Cannot generate Box ID: Multiple Warehouse permissions found for user {user}. Please restrict to a single store.")
        
    user_warehouse = permitted_warehouses[0].for_value
    
    # 2. Fetch the singleton document Cen CRM Settings
    settings_doc = frappe.get_doc("Cen CRM Settings")
    
    # 3. Find matching row
    matching_row = None
    for row in settings_doc.get("store_box_id_configurations", []):
        if row.parent_warehouse == user_warehouse:
            matching_row = row
            break
            
    if not matching_row:
        frappe.throw(f"Cannot generate Box ID: No Box ID configuration found in Cen CRM Settings for warehouse '{user_warehouse}'.")
        
    # 4. Calculate new Box ID
    prefix = matching_row.box_id_prefix or "B"
    try:
        current_num = int(matching_row.current_box_id_number or 0)
    except (ValueError, TypeError):
        current_num = 0
        
    next_number = current_num + 1
    doc.custom_box_id = f"{prefix}-{str(next_number).zfill(4)}"
    
    # 5. Update row and save settings
    matching_row.current_box_id_number = next_number
    settings_doc.save(ignore_permissions=True)
