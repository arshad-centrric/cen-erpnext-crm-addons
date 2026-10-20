import frappe
from cen_crm_addons.api.payment_logic import update_so_payment_status

def execute():
    """
    Recalculates the Payment Status of submitted Sales Orders affected by rounding,
    which were compared against the Grand Total instead of the Rounded Total.
    """
    sales_orders = frappe.db.sql_list("""
        SELECT so.name
        FROM `tabSales Order` so
        WHERE so.docstatus = 1
        AND (
            (so.rounded_total > 0 AND so.rounded_total != so.grand_total)
            OR EXISTS (
                SELECT 1
                FROM `tabSales Invoice Item` sii
                JOIN `tabSales Invoice` si ON si.name = sii.parent
                WHERE sii.sales_order = so.name AND si.docstatus = 1
                AND si.rounded_total > 0 AND si.rounded_total != si.grand_total
            )
        )
    """)

    for sales_order in sales_orders:
        update_so_payment_status(sales_order)
