// Copyright (c) 2026, Centrric Innovations PVT LTD and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cen CRM Settings", {
	setup(frm) {
		frm.set_query("print_format", "quotation_print_formats", function() {
			return { filters: { doc_type: "Quotation" } };
		});
		frm.set_query("print_format", "sales_order_print_formats", function() {
			return { filters: { doc_type: "Sales Order" } };
		});
		
		frm.set_query("parent_warehouse", "store_box_id_configurations", function() {
			return { filters: { is_group: 1 } };
		});
	},
});
