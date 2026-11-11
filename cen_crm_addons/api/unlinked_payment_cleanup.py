import frappe

# One-off cleanup for customer payments left behind when a Sales Order was cancelled and
# ERPNext only unlinked the Payment Entry from it.
#
#   bench --site <site> execute cen_crm_addons.api.unlinked_payment_cleanup.cancel_unlinked_payment_entries
#       lists the payments that would be cancelled and changes nothing (dry run)
#
#   bench --site <site> execute cen_crm_addons.api.unlinked_payment_cleanup.cancel_unlinked_payment_entries \
#       --kwargs "{'dry_run': 0}"
#       cancels them
#
# Optional kwargs: company, from_date, to_date, only_customers_with_cancelled_order (1 = only
# customers who have a cancelled Sales Order).


def get_unlinked_payment_entries(company=None, from_date=None, to_date=None, only_customers_with_cancelled_order=0):
    """Submitted customer receipts that are not linked to any document."""
    conditions = ""
    values = {}

    if company:
        conditions += " AND pe.company = %(company)s"
        values["company"] = company
    if from_date:
        conditions += " AND pe.posting_date >= %(from_date)s"
        values["from_date"] = from_date
    if to_date:
        conditions += " AND pe.posting_date <= %(to_date)s"
        values["to_date"] = to_date
    if int(only_customers_with_cancelled_order):
        conditions += """
            AND EXISTS (
                SELECT 1 FROM `tabSales Order` so
                WHERE so.docstatus = 2 AND so.customer = pe.party AND so.company = pe.company
            )"""

    return frappe.db.sql(f"""
        SELECT
            pe.name, pe.posting_date, pe.company, pe.party, pe.party_name, pe.mode_of_payment,
            pe.paid_amount, pe.unallocated_amount, pe.custom_box_id,
            EXISTS (
                SELECT 1 FROM `tabSales Order` so
                WHERE so.docstatus = 2 AND so.customer = pe.party AND so.company = pe.company
            ) AS customer_has_cancelled_order
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
            AND pe.payment_type = 'Receive'
            AND pe.party_type = 'Customer'
            -- not allocated to a Sales Order, Sales Invoice or any other document
            AND NOT EXISTS (
                SELECT 1 FROM `tabPayment Entry Reference` per WHERE per.parent = pe.name
            )
            -- not used as an advance on a live Sales Invoice
            AND NOT EXISTS (
                SELECT 1 FROM `tabSales Invoice Advance` adv
                JOIN `tabSales Invoice` si ON si.name = adv.parent AND si.docstatus = 1
                WHERE adv.reference_name = pe.name
            )
            -- not referenced by a live Journal Entry
            AND NOT EXISTS (
                SELECT 1 FROM `tabJournal Entry Account` jea
                WHERE jea.reference_type = 'Payment Entry' AND jea.reference_name = pe.name AND jea.docstatus = 1
            )
            -- not matched to a bank transaction
            AND NOT EXISTS (
                SELECT 1 FROM `tabBank Transaction Payments` btp
                WHERE btp.payment_document = 'Payment Entry' AND btp.payment_entry = pe.name
            )
            -- not allocated to anything in the payment ledger (e.g. through Payment Reconciliation)
            AND NOT EXISTS (
                SELECT 1 FROM `tabPayment Ledger Entry` ple
                WHERE ple.voucher_type = 'Payment Entry' AND ple.voucher_no = pe.name
                    AND ple.against_voucher_no != ple.voucher_no AND ple.delinked = 0
            )
            {conditions}
        ORDER BY pe.posting_date, pe.name
    """, values, as_dict=True)


def cancel_unlinked_payment_entries(
    dry_run=1, company=None, from_date=None, to_date=None, only_customers_with_cancelled_order=0, commit=1
):
    """Cancel the customer Payment Entries that are not linked to any document.

    Runs as a dry run unless dry_run is 0. Each payment is cancelled and committed on its own,
    so one failure does not stop the rest.
    """
    dry_run = int(dry_run)
    rows = get_unlinked_payment_entries(company, from_date, to_date, only_customers_with_cancelled_order)

    print(f"{len(rows)} unlinked customer Payment Entries, total {sum(r.paid_amount for r in rows):,.2f}")
    for r in rows:
        flag = "cancelled order exists" if r.customer_has_cancelled_order else "no cancelled order"
        print(f"  {r.name}  {r.posting_date}  {r.party} {r.party_name or ''}  {r.paid_amount:,.2f}  {r.mode_of_payment or ''}  ({flag})")

    if dry_run:
        print("Dry run: nothing was changed. Run again with --kwargs \"{'dry_run': 0}\" to cancel them.")
        return {"cancelled": [], "failed": [], "candidates": [r.name for r in rows]}

    cancelled, failed = [], []
    for r in rows:
        try:
            pe = frappe.get_doc("Payment Entry", r.name)
            pe.flags.ignore_permissions = True
            pe.add_comment("Info", "Cancelled by cleanup: this payment was not linked to any document.")
            pe.cancel()
            if int(commit):
                frappe.db.commit()
            cancelled.append(r.name)
        except Exception as e:
            frappe.db.rollback()
            failed.append({"name": r.name, "error": str(e)})
            frappe.log_error(title=f"Unlinked Payment Entry cleanup failed for {r.name}", message=frappe.get_traceback())

    print(f"Cancelled {len(cancelled)}, failed {len(failed)}")
    for f in failed:
        print(f"  FAILED {f['name']}: {f['error']}")
    return {"cancelled": cancelled, "failed": failed}
