import frappe
from cen_crm_addons.api.roles.pos_user import setup_pos_operator_role
from cen_crm_addons.api.roles.pack_user import setup_pack_user_role
from cen_crm_addons.api.roles.delivery_user import setup_delivery_user_role
from cen_crm_addons.api.roles.purchase_user import setup_purchase_user_role
from cen_crm_addons.api.docperm_setup import setup_custom_permissions

def fix_permissions():
    # List of core doctypes that got corrupted by the old scripts
    doctypes_to_clean = [
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
    
    for dt in doctypes_to_clean:
        if frappe.db.exists("DocType", dt):
            frappe.db.delete("Custom DocPerm", {"parent": dt})
    frappe.db.commit()
    frappe.clear_cache()

    setup_pos_operator_role()
    
    setup_pack_user_role()
    
    setup_delivery_user_role()
    
    setup_purchase_user_role()
    
    setup_custom_permissions()
    
    print("Successfully restored all roles and permissions.")
