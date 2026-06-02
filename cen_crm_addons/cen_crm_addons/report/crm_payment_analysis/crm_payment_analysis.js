// Copyright (c) 2026, Centrric Innovations PVT LTD and contributors
// For license information, please see license.txt

frappe.query_reports["CRM Payment Analysis"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "User",
			"get_query": function() {
				return {
					query: "cen_crm_addons.cen_crm_addons.report.crm_performance.crm_performance.get_sales_users"
				};
			}
		},
		{
			"fieldname": "customer",
			"label": __("Customer ID"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "box_id",
			"label": __("Box ID"),
			"fieldtype": "Data"
		},
		{
			"fieldname": "mode_of_payment",
			"label": __("Mode of Payment"),
			"fieldtype": "Link",
			"options": "Mode of Payment"
		}
	]
};
