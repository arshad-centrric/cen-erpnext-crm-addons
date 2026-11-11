// The Sales Person list follows the company and branch, so a person picked earlier may no longer be in it
function clear_sales_person_and_refresh(report) {
	if (report.get_filter_value("sales_person")) {
		report.set_filter_value("sales_person", "");
	} else {
		report.refresh(true);
	}
}

frappe.query_reports["CRM Performance"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"on_change": function(report) {
				// A branch belongs to one company, so a branch picked for another company no longer applies
				if (report.get_filter_value("branch")) {
					report.set_filter_value("branch", "");
				} else {
					clear_sales_person_and_refresh(report);
				}
			}
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch",
			"get_query": function() {
				const company = frappe.query_report.get_filter_value("company");
				return company ? { filters: { custom_cen_default_company: company } } : {};
			},
			"on_change": function(report) {
				clear_sales_person_and_refresh(report);
			}
		},
		{
			"fieldname": "sales_person",
			"label": __("Sales Person"),
			"fieldtype": "Link",
			"options": "User",
			"get_query": function() {
				return {
					query: "cen_crm_addons.cen_crm_addons.report.crm_performance.crm_performance.get_sales_users",
					filters: {
						company: frappe.query_report.get_filter_value("company"),
						branch: frappe.query_report.get_filter_value("branch")
					}
				};
			}
		}
	],
	"formatter": function(value, row, column, data, default_formatter) {
		// Intercept only our specific column
		if (column.fieldname === "opp_to_so_percent") {
			// Safely identify the Total row (Frappe often makes 'data' undefined or sets 'is_total_row')
			if (!data || data.is_total_row || (data.sales_person && data.sales_person.includes("Total"))) {
				return ""; // Hide the value by returning a blank string
			}
		}
		// Fallback to default for everything else
		if (default_formatter) {
			return default_formatter(value, row, column, data);
		}
		return value;
	}
};
