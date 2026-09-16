import frappe

def generate_box_id(doc, method):
    """Generates a sequential Box ID for Opportunities using Cen CRM Settings."""
    if doc.get("custom_box_id"):
        return

    # Phase 2: Branch-dependent logic
    branch_name = doc.get("custom_cen_branch")
    
    if not branch_name:
        default_branch = frappe.db.get_value("Branch User", {"user": frappe.session.user, "is_default": 1}, "parent")
        if default_branch:
            doc.custom_cen_branch = default_branch
            branch_name = default_branch
        else:
            frappe.throw("Please select a Branch, or ask an Administrator to assign a Default Branch to your user account.")
        
    # 2. Fetch the singleton document Cen CRM Settings
    settings_doc = frappe.get_doc("Cen CRM Settings")
    
    # 3. Find matching row
    matching_row = None
    for row in settings_doc.get("store_box_id_configurations", []):
        if row.branch == branch_name:
            matching_row = row
            break
            
    if not matching_row:
        frappe.throw(f"No Box ID configuration found for branch {branch_name} in Cen CRM Settings.")
        
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
