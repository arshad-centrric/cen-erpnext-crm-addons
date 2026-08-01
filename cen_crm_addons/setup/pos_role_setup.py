import frappe

def create_pos_role_and_perms():
    role_name = "Default POS"

    # 1. Create the Role if it doesn't exist
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1
        }).insert(ignore_permissions=True)
        print(f"Created new Role: {role_name}")
    else:
        print(f"Role {role_name} already exists.")

    # 2. Define Permission Tiers
    tier_1_doctypes = [
        # Core Master Data
        "Item", "Item Price", "Item Group", "Item Barcode", "Brand", "UOM", "UOM Conversion Factor",
        "Company", "Warehouse", "Bin", "Serial No", "Batch",
        
        # POS & Financial Setup
        "POS Profile", "POS Settings", "Mode of Payment", "Account", "Currency",
        
        # Global Settings (Read Only for background validation)
        "Stock Settings", "Accounts Settings", "Selling Settings", "Workspace", "User",
        
        # Taxes & Pricing
        "Sales Taxes and Charges Template", "Item Tax Template", "Tax Rule", "Pricing Rule", 
        
        # Sales Support
        "Sales Person", "Terms and Conditions", "Payment Term", "Payment Terms Template", "Print Format"
    ]
    tier_2_doctypes = ["Customer", "Customer Group", "Territory", "Address", "Contact"]
    tier_3_doctypes = [
        "POS Opening Entry", "POS Invoice", "POS Closing Entry", "POS Invoice Merge Log",
        "Serial and Batch Bundle", "Weigh Scale Settings", "Weigh Scale Condition Rule" # CRITICAL for v15/16 serialized stock transactions
    ]

    from frappe.permissions import setup_custom_perms

    # Helper function to assign permissions
    def assign_perm(doctype, read=1, write=0, create=0, submit=0, cancel=0):
        # Setup custom perms safely copies standard perms if they don't already exist
        setup_custom_perms(doctype)

        # Remove existing custom docperms for this role and doctype to avoid duplicates
        existing = frappe.get_all("Custom DocPerm", filters={"role": role_name, "parent": doctype})
        for doc in existing:
            frappe.delete_doc("Custom DocPerm", doc.name, force=True)

        frappe.get_doc({
            "doctype": "Custom DocPerm",
            "parent": doctype,
            "role": role_name,
            "read": read,
            "write": write,
            "create": create,
            "submit": submit,
            "cancel": cancel,
            "amend": 0,
            "delete": 0,
            "export": 0,
            "import": 0,
            "report": 0,
            "print": 1 if read else 0,
            "email": 0,
            "share": 0
        }).insert(ignore_permissions=True)
        print(f"Assigned permissions for {doctype}")

    # 3. Assign Permissions
    for doctype in tier_1_doctypes:
        assign_perm(doctype, read=1, write=0, create=0, submit=0, cancel=0)

    for doctype in tier_2_doctypes:
        assign_perm(doctype, read=1, write=1, create=1, submit=0, cancel=0)

    for doctype in tier_3_doctypes:
        assign_perm(doctype, read=1, write=1, create=1, submit=1, cancel=1)

    # 4. Commit changes
    frappe.db.commit()
    print(f"Role '{role_name}' and permissions successfully configured.")

    # 5. Grant Page access via Custom Role (prevents modifying standard ERPNext JSON)
    page_name = "point-of-sale"
    
    # Check if a Custom Role already exists for this page
    custom_role_name = frappe.db.get_value("Custom Role", {"page": page_name})
    
    if custom_role_name:
        custom_role = frappe.get_doc("Custom Role", custom_role_name)
        # Append if not already present
        if not any(r.role == role_name for r in custom_role.roles):
            custom_role.append("roles", {"role": role_name})
            custom_role.save(ignore_permissions=True)
            print(f"Added {role_name} to existing Custom Role for {page_name}")
    else:
        # If no Custom Role exists, we must include all standard roles from the Page + our new role,
        # because a Custom Role completely overrides standard Page roles in Frappe.
        page_doc = frappe.get_doc("Page", page_name)
        roles_to_add = [{"role": r.role} for r in page_doc.roles]
        roles_to_add.append({"role": role_name})
        
        frappe.get_doc({
            "doctype": "Custom Role",
            "page": page_name,
            "roles": roles_to_add
        }).insert(ignore_permissions=True)
        print(f"Created new Custom Role for {page_name} with {role_name} access.")
        
    frappe.db.commit()
