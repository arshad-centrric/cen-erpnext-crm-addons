import frappe
import json
def sync_parent_is_bundle(doc, method=None):
    if doc.new_item_code:
        # Check if the parent item has custom_is_product_bundle = 1
        item_is_bundle = frappe.db.get_value("Item", doc.new_item_code, "custom_is_product_bundle")
        
        if not item_is_bundle:
            # Update the item automatically to 1
            frappe.db.set_value("Item", doc.new_item_code, "custom_is_product_bundle", 1)

@frappe.whitelist()
def create_customized_bundle(parent_item_code, new_items_json):
    items_list = json.loads(new_items_json)
    
    # Ensure Item Group exists
    group_name = "Modified Bundles"
    if not frappe.db.exists("Item Group", group_name):
        # Find a suitable parent
        parent = frappe.db.get_value("Item Group", {"is_group": 1}, "name", order_by="lft asc") or "All Item Groups"
        frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": group_name,
            "parent_item_group": parent
        }).insert(ignore_permissions=True)
        
    parent_item = frappe.get_doc("Item", parent_item_code)
    
    # Calculate sequence based on the original parent item count
    existing_items = frappe.db.count("Item", filters={"custom_original_bundle_item": parent_item_code})
    seq = existing_items + 1
    
    # Create new Item - Standard naming will be handled by ERPNext series
    new_item = frappe.new_doc("Item")
    new_item.item_name = f"{parent_item.item_name} (Customized-{seq:02d})"
    new_item.description = f"Customized from Original Bundle: {parent_item_code}"
    new_item.item_group = group_name
    new_item.stock_uom = parent_item.stock_uom
    if parent_item.get("gst_hsn_code"):
        new_item.gst_hsn_code = parent_item.gst_hsn_code
    new_item.is_stock_item = 0
    new_item.custom_is_customized_bundle = 1
    new_item.custom_is_product_bundle = 1
    new_item.custom_original_bundle_item = parent_item_code
    new_item.insert(ignore_permissions=True)
    
    # Use the system-generated ID (e.g. ITEM-0004) for subsequent links
    generated_id = new_item.name
    
    # Inherit standard price via Item Price natively - Copy ALL selling price lists
    parent_prices = frappe.get_all("Item Price", filters={"item_code": parent_item_code, "selling": 1}, fields=["price_list", "price_list_rate"])
    for p in parent_prices:
        price_doc = frappe.new_doc("Item Price")
        price_doc.item_code = generated_id
        price_doc.price_list = p["price_list"]
        price_doc.price_list_rate = p["price_list_rate"]
        price_doc.insert(ignore_permissions=True)
        
    # Create Product Bundle
    bundle = frappe.new_doc("Product Bundle")
    bundle.new_item_code = generated_id
    bundle.custom_is_customized_bundle = 1
    bundle.custom_original_bundle_item = parent_item_code
    bundle.description = f"Customized bundle derived from {parent_item_code}"
    
    for item in items_list:
        bundle.append("items", {
            "item_code": item.get("item_code"),
            "qty": float(item.get("qty", 0))
        })
        
    bundle.insert(ignore_permissions=True)
    
    # Add activity log to the Item
    new_item.add_comment("Comment", f"Customized bundle generated from **{parent_item_code}** by {frappe.session.user}")
    
    return generated_id
