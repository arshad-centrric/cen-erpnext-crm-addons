# Copyright (c) 2026, Centrric Innovations PVT LTD and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TaxRoutingSettings(Document):
	def validate(self):
		seen = set()
		for row in self.mappings:
			if row.company in seen:
				frappe.throw(_("Row {0}: Duplicate mapping for {1}").format(row.idx, frappe.bold(row.company)))
			seen.add(row.company)

			template = frappe.db.get_value(
				"Sales Taxes and Charges Template",
				row.sales_taxes_and_charges_template,
				["company", "disabled", "tax_category"],
				as_dict=True,
			)

			if template.company != row.company:
				frappe.throw(
					_("Row {0}: {1} belongs to {2}, not {3}").format(
						row.idx,
						frappe.bold(row.sales_taxes_and_charges_template),
						frappe.bold(template.company),
						frappe.bold(row.company),
					)
				)

			if template.disabled:
				frappe.throw(
					_("Row {0}: {1} is disabled").format(row.idx, frappe.bold(row.sales_taxes_and_charges_template))
				)

			if not template.tax_category:
				frappe.throw(
					_("Row {0}: {1} has no Tax Category. Set one on the template first").format(
						row.idx, frappe.bold(row.sales_taxes_and_charges_template)
					)
				)

			row.tax_category = template.tax_category
