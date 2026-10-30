def sync_packed_item_target_warehouse(doc, method=None):
    """
    Keeps the Customer Warehouse (target_warehouse) of combo content rows (Packed Item)
    the same as their parent item row, which is what ERPNext intends.

    Frappe fills empty Warehouse fields with the user's default Warehouse (User Permission
    marked "Is Default") when a document is inserted. Combo content rows are created with an
    empty Customer Warehouse, so they were filled with that default. That either stopped the
    save ("Delivery Warehouse and Customer Warehouse can not be same") or silently moved
    stock into the user's default warehouse.

    Runs on before_validate, which is after Frappe fills the defaults and before ERPNext validates.
    """
    packed_items = doc.get("packed_items")
    if not packed_items:
        return

    parent_targets = {row.name: row.get("target_warehouse") for row in doc.get("items") or []}

    for packed_item in packed_items:
        expected = parent_targets.get(packed_item.get("parent_detail_docname"))
        if (packed_item.get("target_warehouse") or None) != (expected or None):
            packed_item.target_warehouse = expected or None
