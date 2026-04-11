import frappe

def ensure_role(role_name):
    """
    Ensures that a Role exists in the system.
    """
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1
        }).insert(ignore_permissions=True)
        frappe.db.commit()

def set_permission(doctype, role, perm_dict):
    """
    Safely creates or updates a Custom DocPerm record.
    """
    # Find existing permission record for this Doctype and Role
    perm_name = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role}, "name")
    
    if perm_name:
        doc = frappe.get_doc("Custom DocPerm", perm_name)
    else:
        # Create new if doesn't exist
        doc = frappe.new_doc("Custom DocPerm")
        doc.parent = doctype
        doc.role = role
    
    # Explicitly reset common bits before applying the matrix to ensure idempotency
    # We want to make sure if a permission is not in the dict, it defaults to 0
    standard_permissions = [
        "read", "write", "create", "delete", "submit", "cancel", "amend", 
        "print", "email", "report", "import", "export", "set_user_permissions", "share"
    ]
    
    for p in standard_permissions:
        doc.set(p, 0)
        
    # Apply the required matrix values
    for field, value in perm_dict.items():
        doc.set(field, value)
    
    doc.save(ignore_permissions=True)

def setup_custom_permissions():
    """
    Enforces the CRM permission matrix for custom roles programmatically.
    """
    # Ensure custom roles exist to prevent LinkValidationError during migration
    for role in ["Sales Person", "Sales Manager", "Supervisor"]:
        ensure_role(role)
    
    # 1. Item Price (Fix for auto-fetch bug)
    set_permission("Item Price", "Sales Person", {"read": 1})
    set_permission("Item Price", "Sales Manager", {"read": 1, "write": 1, "create": 1})
    
    # 2. Opportunity
    set_permission("Opportunity", "Sales Person", {
        "read": 1, "write": 1, "create": 1, "print": 1, "email": 1, "report": 0
    })
    set_permission("Opportunity", "Sales Manager", {
        "read": 1, "write": 1, "create": 1, "print": 1, "email": 1, "report": 1, "delete": 1
    })
    
    # 3. Quotation
    set_permission("Quotation", "Sales Person", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "print": 1, "email": 1, "report": 0
    })
    set_permission("Quotation", "Sales Manager", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1, "print": 1, "email": 1, "report": 1, "delete": 1
    })
    
    # 4. Sales Order
    set_permission("Sales Order", "Sales Person", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "print": 1, "email": 1, "report": 0
    })
    set_permission("Sales Order", "Sales Manager", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1, "amend": 1, "print": 1, "email": 1, "report": 1, "delete": 1
    })
    
    # 5. Payment Entry
    set_permission("Payment Entry", "Sales Person", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "print": 1
    })
    set_permission("Payment Entry", "Supervisor", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "print": 1
    })
    
    # 6. Delivery Note
    set_permission("Delivery Note", "Supervisor", {
        "read": 1, "write": 1, "create": 1, "submit": 1, "print": 1
    })
    
    # 7. Page (Required for Workspaces/UI navigation)
    set_permission("Page", "Sales Person", {"read": 1})
    set_permission("Page", "Supervisor", {"read": 1})
    
    # 8. Workspace (Required for Sidebar visibility in V15)
    set_permission("Workspace", "Sales Person", {"read": 1})
    set_permission("Workspace", "Supervisor", {"read": 1})
    
    # 9. Mode of Payment (Required for Payment Entry defaults)
    set_permission("Mode of Payment", "Sales Person", {"read": 1})
    set_permission("Mode of Payment", "Supervisor", {"read": 1})
    
    # 10. Account & Company (Required for Payment Entry fields)
    set_permission("Account", "Sales Person", {"read": 1})
    set_permission("Account", "Supervisor", {"read": 1})
    set_permission("Company", "Sales Person", {"read": 1})
    set_permission("Company", "Supervisor", {"read": 1})

    # --- Native DocType Permissions (Resolves Ghost Module Issue) ---
    
    # Permission for Cen CRM Settings (Single DocType)
    # Sales Person needs Read to allow Workspace rendering
    set_permission("Cen CRM Settings", "Sales Person", {
        "read": 1
    })
    
    # Sales Manager / Supervisor needs full control
    # Note: If your role is named "Supervisor", ensure you match the Role name below
    set_permission("Cen CRM Settings", "Sales Manager", {
        "read": 1,
        "write": 1,
        "create": 1
    })
    
    # Also granting Supervisor read/write to be safe if that is your primary role
    if frappe.db.exists("Role", "Supervisor"):
        set_permission("Cen CRM Settings", "Supervisor", {
            "read": 1,
            "write": 1,
            "create": 1
        })
    
    frappe.db.commit()
