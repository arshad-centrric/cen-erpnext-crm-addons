// Tax Routing: show the company's Tax Category and item taxes on the form before the first save.
// api/tax_routing.py repeats the same fill on save, so this only has to make the open form match.

frappe.ui.form.on("Quotation", {
	refresh(frm) {
		cen_tax_routing(frm);
	},
	company(frm) {
		cen_tax_routing(frm);
	},
	party_name(frm) {
		// picking the party resets the Tax Category to the party's own (blank) value
		frappe.after_ajax(() => cen_tax_routing(frm));
	},
});

frappe.ui.form.on("Quotation Item", {
	item_code(frm) {
		frappe.after_ajax(() => cen_tax_routing(frm));
	},
});

function cen_tax_routing(frm) {
	if (frm.doc.docstatus !== 0 || !frm.doc.company || !frappe.model.can_write(frm.doctype)) return;
	if (frm.__cen_tax_routing_busy) return;

	const rows_missing_tax = (frm.doc.items || []).some((row) => row.item_code && !row.item_tax_template);
	if (frm.doc.tax_category && !rows_missing_tax) return;

	frm.__cen_tax_routing_busy = true;
	frappe.call({
		method: "cen_crm_addons.api.tax_routing.get_tax_routing_details",
		args: { doc: frm.doc },
		callback(r) {
			frm.__cen_tax_routing_busy = false;
			const details = r.message;
			if (!details) return;

			if (details.tax_category && !frm.doc.tax_category) {
				frm.set_value("tax_category", details.tax_category);
			}
			if (details.taxes_and_charges && !frm.doc.taxes_and_charges) {
				frm.set_value("taxes_and_charges", details.taxes_and_charges);
			}

			// Setting the template fires ERPNext's own handler, which loads the rate and recalculates
			(frm.doc.items || []).forEach((row) => {
				const template = details.items && details.items[row.name];
				if (template && !row.item_tax_template) {
					frappe.model.set_value(row.doctype, row.name, "item_tax_template", template);
				}
			});
		},
		error() {
			frm.__cen_tax_routing_busy = false;
		},
	});
}
