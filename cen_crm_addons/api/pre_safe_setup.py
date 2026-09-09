import frappe

def enforce_standard_permissions_first():
    """
    Runs before any custom permission scripts during migration to ensure 
    Frappe's default standard permissions are safely copied into Custom DocPerm 
    before they get accidentally overwritten by blind custom role insertions.
    """
    # Doctypes touched by any of our scripts or docperm_setup.py
    doctypes_to_protect = [
        "Weigh Scale Settings", "Driver", "Customer", "Cen CRM Settings", "Price List", "Terms and Conditions",
        "Delivery Info Detail", "UOM Conversion Factor", "Box ID Configuration Item", "Tax Rule", "POS Closing Entry", "Loyalty Program",
        "Cost Center", "UOM", "Supplier Group", "Delivery Note", "Bin", "Bank Account",
        "Company", "Territory", "Opportunity", "Item Barcode", "CRM Mobile Print Config", "Payment Terms Template",
        "Purchase Receipt", "Vehicle", "POS Opening Entry", "Batch", "Mobile Allowed Warehouse", "Purchase Order",
        "Page", "Quotation", "Sales Invoice", "Item Group", "Serial No", "Stock Settings",
        "Contact", "Purchase Taxes and Charges Template", "Address", "Workspace", "Item Tax Template", "Mode of Payment",
        "Pricing Rule", "Tax Category", "Serial and Batch Bundle", "Mobile User Profile", "Account", "Delivery Partner",
        "Item Price", "Payment Entry", "Accounts Settings", "Selling Settings", "POS Invoice Merge Log", "Item",
        "Incoterm", "Transporter", "Sales Order", "Shipping Rule", "Branch", "Sales Taxes and Charges Template",
        "Buying Settings", "User", "Warehouse", "Sales Person", "Brand", "Purchase Invoice",
        "Supplier", "POS Profile", "Currency", "POS Settings", "POS Invoice", "Customer Group"
    ]
    
    for dt in doctypes_to_protect:
        if frappe.db.exists("DocType", dt) and not frappe.db.exists("Custom DocPerm", {"parent": dt}):
            try:
                # Force Frappe to fetch fresh JSON metadata bypassing corrupted cache
                meta = frappe.get_meta(dt, cached=False)
                for perm in meta.permissions:
                    custom_perm = frappe.new_doc("Custom DocPerm")
                    custom_perm.update(perm.as_dict())
                    custom_perm.parent = dt
                    custom_perm.parenttype = "DocType"
                    custom_perm.parentfield = "permissions"
                    custom_perm.name = None
                    custom_perm.insert(ignore_permissions=True)
            except Exception:
                pass
    frappe.db.commit()
