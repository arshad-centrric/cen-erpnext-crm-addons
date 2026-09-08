import frappe

def setup_delivery_user_role():
    role_name = "Delivery User (Cen)"

    # 1. Create the Role
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1
        }).insert(ignore_permissions=True)
        print(f"Created new role: {role_name}")
    else:
        print(f"Role '{role_name}' already exists.")

    # 2. Clear existing custom permissions to ensure a clean slate
    frappe.db.delete("Custom DocPerm", {"role": role_name})
    print("Cleared old permissions.")

    # 3. Define the exact permission map
    permissions_map = {
        # Transactions
        "Sales Order": {"read": 1, "write": 1},
        "Sales Invoice": {"read": 1},
        "Delivery Note": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},

        # Core CRM / Master
        "Customer": {"read": 1, "write": 1, "create": 1},
        "Address": {"read": 1, "write": 1, "create": 1},
        "Contact": {"read": 1, "write": 1, "create": 1},

        # Settings
        "Stock Settings": {"read": 1},
        "Selling Settings": {"read": 1},
        "Accounts Settings": {"read": 1},

        # Master Data for Billing, Delivery & Items
        "Company": {"read": 1},
        "Branch": {"read": 1},
        "Workspace": {"read": 1},
        "User": {"read": 1},
        "Currency": {"read": 1},
        "Item": {"read": 1},
        "Item Price": {"read": 1},
        "Item Group": {"read": 1},
        "Item Barcode": {"read": 1},
        "Item Tax Template": {"read": 1},
        "Brand": {"read": 1},
        "UOM": {"read": 1},
        "UOM Conversion Factor": {"read": 1},
        "Price List": {"read": 1},
        "Pricing Rule": {"read": 1},
        "Sales Taxes and Charges Template": {"read": 1},
        "Tax Rule": {"read": 1},
        "Warehouse": {"read": 1},
        "Bin": {"read": 1},
        "Mode of Payment": {"read": 1},
        "Account": {"read": 1},
        "Customer Group": {"read": 1},
        "Territory": {"read": 1},
        "Tax Category": {"read": 1},
        "Cost Center": {"read": 1},
        "Sales Person": {"read": 1},
        "Terms and Conditions": {"read": 1},
        "Payment Terms Template": {"read": 1},
        "Loyalty Program": {"read": 1},
        
        # Serial and Batch
        "Serial No": {"read": 1, "write": 1},
        "Batch": {"read": 1},
        "Serial and Batch Bundle": {"read": 1, "write": 1, "create": 1},

        # Custom App Specific (Box & Mobile logic)
        "Box ID Configuration Item": {"read": 1},
        "Mobile User Profile": {"read": 1},
        "Mobile Allowed Warehouse": {"read": 1},
        "CRM Mobile Print Config": {"read": 1},
        "Delivery Partner": {"read": 1},
        "Delivery Info Detail": {"read": 1}
    }

    # 4. Loop through and apply permissions safely
    for doctype, perms in permissions_map.items():
        if not frappe.db.exists("DocType", doctype):
            print(f"Skipped: {doctype} (DocType not found in this site)")
            continue
        
        try:
            frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": doctype,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": role_name,
                **perms
            }).insert(ignore_permissions=True)
            print(f"Mapped: {doctype}")
        except Exception as e:
            print(f"Failed on {doctype}: {str(e)}")

    # 5. Save to database and force cache clear
    frappe.db.commit()
    frappe.clear_cache()
    print("\nSUCCESS: All roles and permissions have been committed to the database.")

