// Tax Routing (sales): show the company's Tax Category and item taxes on the form before the first save.
// api/tax_routing.py repeats the same fill on save, so this only has to make the open form match.
// This one file is mapped to three doctypes, so it can be loaded more than once per session:
// register the handlers only the first time.
(function () {
	if (window.cen_sales_tax_routing_registered) return;
	window.cen_sales_tax_routing_registered = true;

	const CEN_SALES_TAX_ROUTING = {
		Quotation: { item_doctype: "Quotation Item", party_field: "party_name" },
		"Sales Order": { item_doctype: "Sales Order Item", party_field: "customer" },
		"Sales Invoice": { item_doctype: "Sales Invoice Item", party_field: "customer" },
	};

	Object.entries(CEN_SALES_TAX_ROUTING).forEach(([doctype, { item_doctype, party_field }]) => {
		const handlers = {
			refresh(frm) {
				cen_tax_routing(frm);
			},
			company(frm) {
				cen_tax_routing(frm);
			},
			// ERPNext and India Compliance run more lookups after the party is picked (address tax category,
			// GST details) and can reset these two fields once more; keep the routed values for a few seconds
			tax_category(frm) {
				cen_keep_route(frm);
			},
			taxes_and_charges(frm) {
				cen_keep_route(frm);
			},
		};
		// picking the party resets the Tax Category to the party's own (blank) value
		handlers[party_field] = function (frm) {
			frappe.after_ajax(() => cen_tax_routing(frm, true));
		};
		frappe.ui.form.on(doctype, handlers);

		frappe.ui.form.on(item_doctype, {
			item_code(frm) {
				frappe.after_ajax(() => cen_tax_routing(frm));
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
			if (frm.doc[CEN_SALES_TAX_ROUTING[frm.doctype].party_field] !== route.party) return;

			for (const field of ["taxes_and_charges", "tax_category"]) {
				if (route[field] && frm.doc[field] !== route[field]) {
					route.fixes += 1;
					route.until = Math.max(route.until, Date.now() + 3000);
					await frm.set_value(field, route[field]);
				}
			}
		}, 400);
	}

	// replace_template: the party was just picked, so the template ERPNext / India Compliance loaded with it
	// is theirs, not a choice made by hand
	function cen_tax_routing(frm, replace_template) {
		if (frm.doc.docstatus !== 0 || !frm.doc.company || !frappe.model.can_write(frm.doctype)) return;
		// ERPNext clears the Tax Category again while no party is selected, so wait for it
		const party_field = CEN_SALES_TAX_ROUTING[frm.doctype].party_field;
		if (!frm.doc[party_field]) return;
		// returns and POS invoices already carry their own taxes
		if (frm.doc.is_return || frm.doc.is_pos || frm.__cen_tax_routing_busy) return;

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
						party: frm.doc[CEN_SALES_TAX_ROUTING[frm.doctype].party_field],
						tax_category: details.tax_category,
						taxes_and_charges: details.taxes_and_charges,
						until: Date.now() + 8000,
						fixes: 0,
					};
				}

				// After picking the party the routed template replaces the one loaded with it
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
