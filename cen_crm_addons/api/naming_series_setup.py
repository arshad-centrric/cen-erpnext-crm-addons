import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

def setup_customer():
    """
    Enforces Customer naming by Naming Series and sets CUS-.## as default.
    """
    # 1. Update Selling Settings: Set naming by "Naming Series"
    selling_settings = frappe.get_doc("Selling Settings")
    if selling_settings.cust_master_name != "Naming Series":
        selling_settings.cust_master_name = "Naming Series"
        selling_settings.save(ignore_permissions=True)
        frappe.db.commit()

    # 2. Update Customer Naming Series Options
    new_option = "C-.#####"
    
    # Force a fresh meta load to get current state
    frappe.clear_cache(doctype="Customer")
    ns_field = frappe.get_meta("Customer").get_field("naming_series")
    
    if ns_field:
        current_options = ns_field.options or ""
        options_list = [opt.strip() for opt in current_options.split("\n") if opt.strip()]
        
        if new_option not in options_list:
            # Add C-.##### as the first option
            options_list.insert(0, new_option)
            updated_options = "\n".join(options_list)
            
            make_property_setter(
                doctype="Customer", 
                fieldname="naming_series", 
                property="options", 
                value=updated_options, 
                property_type="Text"
            )
            # Commit and clear cache so the default validation can see the new options
            frappe.db.commit()
            frappe.clear_cache(doctype="Customer")
    
    # 3. Set Default Naming Series to C-.#####
    make_property_setter(
        doctype="Customer", 
        fieldname="naming_series", 
        property="default", 
        value=new_option, 
        property_type="Text"
    )
    
def setup_item_naming():
    """
    Enforces Item naming by Naming Series and sets ITEM-.## as default.
    """
    # 1. Update Stock Settings
    stock_settings = frappe.get_doc("Stock Settings")
    if stock_settings.item_naming_by != "Naming Series":
        stock_settings.item_naming_by = "Naming Series"
        stock_settings.save(ignore_permissions=True)
        frappe.db.commit()

    # 2. Update Item Naming Series Options
    new_option = "ITEM-.##"
    
    frappe.clear_cache(doctype="Item")
    ns_field = frappe.get_meta("Item").get_field("naming_series")
    
    if ns_field:
        current_options = ns_field.options or ""
        options_list = [opt.strip() for opt in current_options.split("\n") if opt.strip()]
        
        if new_option not in options_list:
            options_list.append(new_option)
            updated_options = "\n".join(options_list)
            
            make_property_setter(
                doctype="Item", 
                fieldname="naming_series", 
                property="options", 
                value=updated_options, 
                property_type="Text"
            )
            frappe.db.commit()
            frappe.clear_cache(doctype="Item")
            
    # 3. Set Default Naming Series
    make_property_setter(
        doctype="Item", 
        fieldname="naming_series", 
        property="default", 
        value=new_option, 
        property_type="Text"
    )
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Item")

def setup_sales_order_naming():
    """
    Sets Sales Order naming series to SO-.YY.-
    """
    new_option = "SO-.YY.-"
    
    frappe.clear_cache(doctype="Sales Order")
    ns_field = frappe.get_meta("Sales Order").get_field("naming_series")
    
    if ns_field:
        current_options = ns_field.options or ""
        options_list = [opt.strip() for opt in current_options.split("\n") if opt.strip()]
        
        if new_option not in options_list:
            # Put SO-.YY.- at the top as first option
            options_list.insert(0, new_option)
            updated_options = "\n".join(options_list)
            
            make_property_setter(
                doctype="Sales Order", 
                fieldname="naming_series", 
                property="options", 
                value=updated_options, 
                property_type="Text"
            )
            frappe.db.commit()
            frappe.clear_cache(doctype="Sales Order")
            
    # Set Default Naming Series
    make_property_setter(
        doctype="Sales Order", 
        fieldname="naming_series", 
        property="default", 
        value=new_option, 
        property_type="Text"
    )
    
    frappe.db.commit()
    frappe.clear_cache(doctype="Sales Order")

def setup_customer_naming():
    """
    Enforces Customer & Item naming by Naming Series and sets defaults.
    """
    setup_customer()
    setup_item_naming()
    setup_sales_order_naming()
