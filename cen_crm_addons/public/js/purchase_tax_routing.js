// Tax Routing (purchase): show the company's Tax Category and item taxes on the form before the first save.
// api/tax_routing.py repeats the same fill on save, so this only has to make the open form match.
// This one file is mapped to four doctypes, so it can be loaded more than once per session:
// register the handlers only the first time.
(function () {
	if (window.cen_purchase_tax_routing_registered) return;
	window.cen_purchase_tax_routing_registered = true;

	const CEN_PURCHASE_TAX_ROUTING = {
		"Supplier Quotation": "Supplier Quotation Item",
		"Purchase Order": "Purchase Order Item",
		"Purchase Receipt": "Purchase Receipt Item",
		"Purchase Invoice": "Purchase Invoice Item",
	};

	Object.entries(CEN_PURCHASE_TAX_ROUTING).forEach(([doctype, item_doctype]) => {
		frappe.ui.form.on(doctype, {
			refresh(frm) {
				cen_purchase_tax_routing(frm);
			},
			company(frm) {
				cen_purchase_tax_routing(frm);
			},
			supplier(frm) {
				// picking the supplier resets the Tax Category to the supplier's own (blank) value
				frappe.after_ajax(() => cen_purchase_tax_routing(frm, true));
			},
			// ERPNext and India Compliance run more lookups after the supplier is picked and can reset these
			// two fields once more; keep the routed values for a few seconds
			tax_category(frm) {
				cen_keep_route(frm);
			},
			taxes_and_charges(frm) {
				cen_keep_route(frm);
			},
		});

		frappe.ui.form.on(item_doctype, {
			item_code(frm) {
				frappe.after_ajax(() => cen_purchase_tax_routing(frm));
			},
		});
	});

	// Late lookups can reset the Tax Category and the template in one go, so look at both together once
	// the burst has settled, template first (ERPNext loads its rows), then the category
	function cen_keep_route(frm) {
		const route = frm.__cen_route;
		if (!route || Date.now() > route.until || route.fixes >= 6) return;

		clearTimeout(frm.__cen_keep_timer);
		frm.__cen_keep_timer = setTimeout(async () => {
			if (frm.doc.supplier !== route.party) return;

			for (const field of ["taxes_and_charges", "tax_category"]) {
				if (route[field] && frm.doc[field] !== route[field]) {
					route.fixes += 1;
					route.until = Math.max(route.until, Date.now() + 3000);
					await frm.set_value(field, route[field]);
				}
			}
		}, 400);
	}

	// replace_template: the supplier was just picked, so the template ERPNext / India Compliance loaded with it
	// is theirs, not a choice made by hand
	function cen_purchase_tax_routing(frm, replace_template) {
		if (frm.doc.docstatus !== 0 || !frm.doc.company || !frappe.model.can_write(frm.doctype)) return;
		if (frm.doc.is_return || frm.__cen_tax_routing_busy) return;

		const rows_missing_tax = (frm.doc.items || []).some((row) => row.item_code && !row.item_tax_template);
		if (frm.doc.tax_category && !rows_missing_tax) return;

		frm.__cen_tax_routing_busy = true;
		frappe.call({
			method: "cen_crm_addons.api.tax_routing.get_tax_routing_details",
			args: { doc: frm.doc, replace_template: replace_template ? 1 : 0 },
			callback(r) {
				frm.__cen_tax_routing_busy = false;
				const details = r.message;
				if (!details) return;

				if (replace_template) {
					frm.__cen_route = {
						party: frm.doc.supplier,
						tax_category: details.tax_category,
						taxes_and_charges: details.taxes_and_charges,
						until: Date.now() + 8000,
						fixes: 0,
					};
				}

				// After picking the supplier the routed template replaces the one loaded with it
				if (
					details.taxes_and_charges &&
					details.taxes_and_charges !== frm.doc.taxes_and_charges &&
					(replace_template || !frm.doc.taxes_and_charges)
				) {
					frm.set_value("taxes_and_charges", details.taxes_and_charges);
				}
				if (details.tax_category && !frm.doc.tax_category) {
					frm.set_value("tax_category", details.tax_category);
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
})();
