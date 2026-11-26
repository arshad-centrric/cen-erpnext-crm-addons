def sync_packed_item_target_warehouse(doc, method=None):
    """
    Clears a Customer Warehouse (target_warehouse) that Frappe's own default-filling put
    there by coincidence, and keeps combo content rows (Packed Item) in step with their
    parent item row, which is what ERPNext intends.

    Frappe fills empty Warehouse fields with the user's default Warehouse (User Permission
    marked "Is Default") when a document is inserted. Both the Delivery Warehouse and the
    Customer Warehouse are blank Warehouse fields, so a user with one default warehouse gets
    the same value filled into both - on the main item row itself, not just on combo content
    rows. ERPNext's own validate_target_warehouse() never allows the two to be equal (there is
    no legitimate case where they should be), so any row where they match was not a deliberate
    choice and the Customer Warehouse is cleared rather than blocking the save. That either
    stopped the save ("Delivery Warehouse and Customer Warehouse can not be same") or, when the
    defaults differed from the delivery warehouse, silently moved stock into the user's default
    warehouse.

    Runs on before_validate, which is after Frappe fills the defaults and before ERPNext validates.
    """
    items = doc.get("items") or []

    for item in items:
        if item.get("target_warehouse") and item.get("target_warehouse") == item.get("warehouse"):
            item.target_warehouse = None

    packed_items = doc.get("packed_items")
    if not packed_items:
        return

    parent_targets = {row.name: row.get("target_warehouse") for row in items}

    for packed_item in packed_items:
        expected = parent_targets.get(packed_item.get("parent_detail_docname"))
        if (packed_item.get("target_warehouse") or None) != (expected or None):
            packed_item.target_warehouse = expected or None


def clear_unused_rejected_warehouse(doc, method=None):
    """
    Clears a Rejected Warehouse that Frappe's own default-filling put there when nothing was
    rejected (Purchase Receipt and Purchase Invoice).

    Frappe fills empty Warehouse fields with the user's default Warehouse (User Permission
    marked "Is Default") when a document is inserted. Rejected Warehouse is one of them, so a
    user whose default warehouse is also the accepted warehouse got "Accepted Warehouse and
    Rejected Warehouse cannot be same" on a receipt with no rejected quantity.

    A Rejected Warehouse is only meaningful for rows with a rejected quantity, so it is cleared
    on every row that has none. On a row that does reject something, a Rejected Warehouse equal
    to its own warehouse is replaced by the header's Rejected Warehouse when there is one, and
    cleared otherwise (ERPNext then asks for it). A different, deliberate Rejected Warehouse is
    never touched. The header field is cleared only when no row rejects anything.

    Runs on before_validate, which is after Frappe fills the defaults and before ERPNext validates.
    """
    from frappe.utils import flt

    any_rejected = False

    for item in doc.get("items") or []:
        if flt(item.get("rejected_qty")):
            any_rejected = True
            if item.get("rejected_warehouse") and item.get("rejected_warehouse") == item.get("warehouse"):
                item.rejected_warehouse = doc.get("rejected_warehouse") or None
        elif item.get("rejected_warehouse"):
            item.rejected_warehouse = None

    if not any_rejected and doc.get("rejected_warehouse"):
        doc.rejected_warehouse = None
