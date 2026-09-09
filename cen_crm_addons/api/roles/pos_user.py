import frappe

def setup_pos_operator_role():
    role_name = "AGT - POS User"

    # 1. Create the Role
    if not frappe.db.exists("Role", role_name):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": 1
        }).insert(ignore_permissions=True)
    else:

    # 2. Clear existing custom permissions to ensure a clean slate
    frappe.db.delete("Custom DocPerm", {"role": role_name})

    # 3. Define the exact permission map
    permissions_map = {
        # Transactions
        "POS Invoice": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        "Sales Invoice": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        "POS Opening Entry": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        "POS Closing Entry": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        "Payment Entry": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
        "POS Invoice Merge Log": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},

        # Quick Entry (Customers)
        "Customer": {"read": 1, "write": 1, "create": 1},
        "Address": {"read": 1, "write": 1, "create": 1},
        "Contact": {"read": 1, "write": 1, "create": 1},

        # Global Settings (The ones that caused the popup errors)
        "POS Settings": {"read": 1},
        "Stock Settings": {"read": 1},
        "Selling Settings": {"read": 1},
        "Accounts Settings": {"read": 1},

        # Master Data
        "POS Profile": {"read": 1},
        "Weigh Scale Settings": {"read": 1},
        "Workspace": {"read": 1},
        "User": {"read": 1},
        "Company": {"read": 1},
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
        "Loyalty Program": {"read": 1},
        "Serial No": {"read": 1, "write": 1},
        "Batch": {"read": 1},
        "Serial and Batch Bundle": {"read": 1, "write": 1, "create": 1}
    }

    # 4. Loop through and apply permissions safely
    for doctype, perms in permissions_map.items():
        if not frappe.db.exists("DocType", doctype):
            continue
        
        try:
            # Safely set up custom permissions to retain standard roles
            if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
                meta = frappe.get_meta(doctype, cached=False)
                for perm in meta.permissions:
                    custom_perm = frappe.new_doc("Custom DocPerm")
                    custom_perm.update(perm.as_dict())
                    custom_perm.parent = doctype
                    custom_perm.parenttype = "DocType"
                    custom_perm.parentfield = "permissions"
                    custom_perm.name = None
                    custom_perm.insert(ignore_permissions=True)
            
            
            # Check if this role already has a Custom DocPerm for this doctype
            name = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role_name, "permlevel": 0})
            if name:
                doc = frappe.get_doc("Custom DocPerm", name)
                doc.update(perms)
                doc.save(ignore_permissions=True)
            else:
                frappe.get_doc({
                    "doctype": "Custom DocPerm",
                    "parent": doctype,
                    "parenttype": "DocType",
                    "parentfield": "permissions",
                    "role": role_name,
                    "permlevel": 0,
                    **perms
                }).insert(ignore_permissions=True)
        except Exception as e:

    # 5. Grant UI Page Access for Point of Sale
    page_name = "point-of-sale"
    if frappe.db.exists("Page", page_name):
        page_doc = frappe.get_doc("Page", page_name)
        
        has_role = any(row.role == role_name for row in page_doc.roles)
        
        if not has_role:
            page_doc.append("roles", {"role": role_name})
            page_doc.save(ignore_permissions=True)

    # 6. Save to database and force cache clear
    frappe.db.commit()
    frappe.clear_cache()
