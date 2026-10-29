// Copyright (c) 2026, Centrric Innovations PVT LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tax Routing Settings", {
	setup(frm) {
		const template_query = function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return { filters: { company: row.company, disabled: 0 } };
		};

		// A company can have only one template per table, so hide the ones already listed
		const company_query = function (table) {
			return function (doc, cdt, cdn) {
				const used = (frm.doc[table] || [])
					.filter((d) => d.name !== cdn && d.company)
					.map((d) => d.company);
				return { filters: [["Company", "name", "not in", used]] };
			};
		};

		frm.set_query("company", "mappings", company_query("mappings"));
		frm.set_query("company", "purchase_mappings", company_query("purchase_mappings"));
		frm.set_query("sales_taxes_and_charges_template", "mappings", template_query);
		frm.set_query("purchase_taxes_and_charges_template", "purchase_mappings", template_query);
	},
});

// Frappe pre-fills a new row's Company with the user's default company; leave it blank so the user picks.
// The "<table>_add" events fire on the child doctype, not on the parent form.
frappe.ui.form.on("Company Tax Mapping", {
	mappings_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "company", null);
	},

	company(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "sales_taxes_and_charges_template", null);
	},
});

frappe.ui.form.on("Purchase Company Tax Mapping", {
	purchase_mappings_add(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "company", null);
	},

	company(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "purchase_taxes_and_charges_template", null);
	},
});
