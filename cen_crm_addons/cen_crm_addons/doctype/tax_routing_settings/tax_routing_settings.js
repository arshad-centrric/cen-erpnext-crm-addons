// Copyright (c) 2026, Centrric Innovations PVT LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Tax Routing Settings", {
	setup(frm) {
		frm.set_query("sales_taxes_and_charges_template", "mappings", function (doc, cdt, cdn) {
			const row = locals[cdt][cdn];
			return { filters: { company: row.company, disabled: 0 } };
		});
	},
});

frappe.ui.form.on("Company Tax Mapping", {
	company(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "sales_taxes_and_charges_template", null);
	},
});
