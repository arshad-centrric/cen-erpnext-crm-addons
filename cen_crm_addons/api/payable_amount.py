from frappe.utils import flt

# Amount the customer is asked to pay: the Rounded Total, or the Grand Total when rounding
# is disabled (ERPNext stores Rounded Total as 0 then). Payment Entries use the same rule.
# A customer who pays the lower of the Grand Total and the Rounded Total has settled the
# document, so a rounding difference never shows as pending.

def get_payable_amount(doc):
    """Returns the payable amount of a Sales Order or Sales Invoice (document or dict)."""
    return flt(doc.get("rounded_total")) or flt(doc.get("grand_total"))

def get_settled_amount(doc):
    """Returns the lowest amount that settles the document (lower of Grand and Rounded Total)."""
    return min(flt(doc.get("grand_total")), get_payable_amount(doc))

def get_pending_amount(doc, paid_amount):
    """Returns what is still due: 0 once the settled amount is paid, else payable minus paid."""
    paid_amount = flt(paid_amount)
    if paid_amount >= flt(get_settled_amount(doc), 2):
        return 0.0
    return flt(get_payable_amount(doc) - paid_amount, 2)

def get_invoice_pending_amount(invoice):
    """Returns what is still due on a Sales Invoice (needs grand_total, rounded_total, outstanding_amount)."""
    paid_amount = get_payable_amount(invoice) - flt(invoice.get("outstanding_amount"))
    return min(get_pending_amount(invoice, paid_amount), flt(invoice.get("outstanding_amount")))

def sql_payable_amount(alias):
    """SQL expression for the payable amount of the table with the given alias."""
    return f"IFNULL(NULLIF({alias}.rounded_total, 0), {alias}.grand_total)"

def sql_settled_amount(alias):
    """SQL expression for the settled amount of the table with the given alias."""
    return f"LEAST({alias}.grand_total, {sql_payable_amount(alias)})"
