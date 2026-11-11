"""Company-wise Tax Category routing for Quotation -> Sales Order -> Sales Invoice and for
Supplier Quotation -> Purchase Order -> Purchase Receipt -> Purchase Invoice.

Item Tax rows on Items are tied to a Tax Category (e.g. "In-State"), but a CRM document never gets
one: the Customer is auto-created from the Lead with no tax details, so no Item Tax Template matches
and every line is taxed at 0. ERPNext only re-resolves item taxes in the browser when the Tax
Category is changed by hand, and it skips rows that have no Item Tax Template yet.

This fills the gap on the server, on every draft save:
  1. Tax Category (and, on a new document, the taxes template) comes from "Tax Routing Settings"
     for the document's company, or from the company's default template when it has no row.
     Sales documents read the Sales table, purchase documents the Purchase table.
  2. Item rows without an Item Tax Template get one resolved from that Tax Category.

Nothing already chosen is overwritten. See docs/tax_routing.md.

Purchases are routed only when GST can actually be claimed on them. India Compliance rejects input
GST on a purchase from a supplier without a GSTIN (or from a composition dealer) unless it is a
reverse charge, so a document like that is left exactly as the user entered it.
"""

import frappe
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from erpnext.stock.get_item_details import get_item_tax_map, get_item_tax_template
from frappe.model.utils import get_fetch_values

SALES = frappe._dict(
	doctypes=("Quotation", "Sales Order", "Sales Invoice"),
	template_doctype="Sales Taxes and Charges Template",
	mappings="mappings",
	template_field="sales_taxes_and_charges_template",
)
PURCHASE = frappe._dict(
	doctypes=("Supplier Quotation", "Purchase Order", "Purchase Receipt", "Purchase Invoice"),
	template_doctype="Purchase Taxes and Charges Template",
	mappings="purchase_mappings",
	template_field="purchase_taxes_and_charges_template",
)


def get_routing_side(doctype):
	"""SALES or PURCHASE for a document type, None when routing does not apply to it."""
	for side in (SALES, PURCHASE):
		if doctype in side.doctypes:
			return side


def apply_company_tax_routing(doc, method=None, replace_template=False):
	side = get_routing_side(doc.doctype)

	# POS invoices already carry the POS Profile's Tax Category and Template
	if not side or doc.docstatus != 0 or doc.get("is_return") or doc.get("is_pos") or not doc.company:
		return

	if side is PURCHASE and not supplier_can_charge_gst(doc):
		return

	route = get_company_tax_route(doc.company, side)
	if not route:
		return

	# A different template picked by hand (or by India Compliance) is left alone, unless the form asks for
	# a replace: picking the party makes ERPNext and India Compliance load a template of their own, which
	# is not a choice made by hand
	if not doc.taxes_and_charges or doc.taxes_and_charges == route.template or replace_template:
		if not doc.tax_category and route.tax_category:
			doc.tax_category = route.tax_category

		# Only on a new document, so taxes removed on purpose from a saved draft stay removed
		if (replace_template and doc.taxes_and_charges != route.template) or (
			doc.is_new() and not doc.taxes_and_charges and not doc.taxes
		):
			doc.taxes_and_charges = route.template
			doc.set("taxes", [])
			doc.extend("taxes", get_taxes_and_charges(side.template_doctype, route.template))

	if doc.tax_category:
		set_missing_item_taxes(doc)


@frappe.whitelist()
def get_tax_routing_details(doc, replace_template=0):
	"""What the save hook would set on the open form, so it shows before the first save.

	The form sets the Item Tax Template on each row and ERPNext's own row handler then loads the
	rate and recalculates, exactly as if it had been picked by hand.
	"""
	doc = frappe.get_doc(frappe.parse_json(doc))
	if not get_routing_side(doc.doctype):
		frappe.throw(frappe._("Tax routing does not apply to {0}").format(doc.doctype))

	frappe.has_permission(doc.doctype, "read", throw=True)
	apply_company_tax_routing(doc, replace_template=frappe.utils.cint(replace_template))

	return {
		"tax_category": doc.tax_category,
		"taxes_and_charges": doc.taxes_and_charges,
		"items": {row.name: row.item_tax_template for row in doc.items if row.item_tax_template},
	}


def supplier_can_charge_gst(doc):
	"""Whether input GST can be put on this purchase without India Compliance rejecting it."""
	if not doc.get("supplier") or doc.get("is_reverse_charge"):
		return False

	supplier = frappe.get_cached_doc("Supplier", doc.supplier)
	if (doc.get("gst_category") or supplier.get("gst_category")) == "Registered Composition":
		return False

	# GSTIN of the document's supplier address, else of the supplier itself
	gstin = doc.get("supplier_gstin")
	if not gstin and doc.get("supplier_address"):
		gstin = frappe.db.get_value("Address", doc.supplier_address, "gstin")

	return bool(gstin or supplier.get("gstin"))


def get_company_tax_route(company, side=SALES):
	"""The company's row in Tax Routing Settings, else its default Taxes and Charges Template."""
	for row in frappe.get_cached_doc("Tax Routing Settings").get(side.mappings):
		if row.company == company:
			template = row.get(side.template_field)
			return frappe._dict(
				template=template,
				tax_category=frappe.get_cached_value(side.template_doctype, template, "tax_category"),
			)

	template = frappe.db.get_value(
		side.template_doctype, {"company": company, "is_default": 1, "disabled": 0}, ["name", "tax_category"], as_dict=True
	)
	if template:
		return frappe._dict(template=template.name, tax_category=template.tax_category)


def set_missing_item_taxes(doc):
	"""Resolve the Item Tax Template for rows that have none, as Get Item Details does."""
	transaction_date = doc.get("transaction_date") or doc.get("posting_date")

	for row in doc.items:
		if not row.item_code or row.item_tax_template:
			continue

		template = get_item_tax_template(
			{
				"company": doc.company,
				"tax_category": doc.tax_category,
				"base_net_rate": row.base_net_rate,
				"transaction_date": transaction_date,
				# a purchase invoice takes its tax validity from the supplier's bill date first
				"bill_date": doc.get("bill_date"),
			},
			frappe.get_cached_doc("Item", row.item_code),
		)
		if not template:
			continue

		row.item_tax_template = template
		row.item_tax_rate = get_item_tax_map(doc=doc, tax_template=template, as_json=True)
		# e.g. India Compliance's GST Treatment, fetched from the Item Tax Template
		row.update(get_fetch_values(row.doctype, "item_tax_template", template))
