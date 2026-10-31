import frappe
from frappe.utils import flt


def clear_default_rejected_warehouse(doc, method=None):
    """
    Clears a Rejected Warehouse on Purchase Receipt items that was only filled in from the
    user's default Warehouse.

    Frappe fills empty Warehouse fields with the user's default Warehouse (User Permission
    marked "Is Default") when a document is inserted. APIs such as create_purchase_receipt
    never send a Rejected Warehouse, so it was filled with that default. That either stopped
    the save ("Accepted Warehouse and Rejected Warehouse cannot be same") or saved a wrong
    Rejected Warehouse on the receipt.

    Only a value that matches the default Frappe fills in, on a row with no rejected qty, is
    cleared. A Rejected Warehouse entered on purpose is never touched.

    Runs on before_validate, which is after Frappe fills the defaults and before ERPNext validates.
    """
    rows = doc.get("items")
    if not rows or not doc.is_new():
        return

    defaults = frappe.new_doc(rows[0].doctype, parent_doc=doc, parentfield="items", as_dict=True)
    default_warehouse = defaults.get("rejected_warehouse")
    if not default_warehouse:
        return

    for row in rows:
        if row.get("rejected_warehouse") == default_warehouse and not flt(row.get("rejected_qty")):
            row.rejected_warehouse = None
