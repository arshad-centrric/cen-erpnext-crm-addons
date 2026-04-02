import frappe

def sync_parent_is_bundle(doc, method=None):
    if doc.new_item_code:
        # Check if the parent item has custom_is_product_bundle = 1
        item_is_bundle = frappe.db.get_value("Item", doc.new_item_code, "custom_is_product_bundle")
        
        if not item_is_bundle:
            # Update the item automatically to 1
            frappe.db.set_value("Item", doc.new_item_code, "custom_is_product_bundle", 1)
