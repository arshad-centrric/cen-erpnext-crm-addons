import frappe
from frappe import _

# Purchase Order statuses that can still be received against.
# Used by the web dropdown filter (public/js/purchase_receipt.js) and the mobile APIs.
RECEIVABLE_PO_STATUSES = ("To Receive and Bill",)


def validate_purchase_order_link(doc, method=None):
	"""
	Keep the header field `custom_purchase_order` in sync with the item rows.

	- If it is empty and every PO-linked item row points to the same Purchase Order
	  (e.g. receipt made from web "Get Items From"), fill it in.
	- If it is set, make sure the Purchase Order belongs to the same supplier and company.
	"""
	if not doc.get("custom_purchase_order"):
		linked_pos = {row.purchase_order for row in doc.get("items") if row.get("purchase_order")}
		if len(linked_pos) == 1:
			doc.custom_purchase_order = linked_pos.pop()
		return

	po = frappe.db.get_value(
		"Purchase Order",
		doc.custom_purchase_order,
		["supplier", "company", "docstatus"],
		as_dict=True,
	)
	if not po:
		frappe.throw(_("Purchase Order {0} not found").format(doc.custom_purchase_order))

	if po.docstatus != 1:
		frappe.throw(_("Purchase Order {0} must be submitted").format(doc.custom_purchase_order))

	if doc.supplier and po.supplier != doc.supplier:
		frappe.throw(
			_("Purchase Order {0} belongs to Supplier {1}, not {2}").format(
				doc.custom_purchase_order, po.supplier, doc.supplier
			)
		)

	if doc.company and po.company != doc.company:
		frappe.throw(
			_("Purchase Order {0} belongs to Company {1}, not {2}").format(
				doc.custom_purchase_order, po.company, doc.company
			)
		)
