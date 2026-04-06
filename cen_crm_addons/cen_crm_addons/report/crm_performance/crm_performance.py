import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary

def get_columns():
	return [
		{
			"label": _("Sales Person"),
			"fieldname": "sales_person",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Total Leads"),
			"fieldname": "total_leads",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Total Opportunities"),
			"fieldname": "total_opportunities",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Total Quotations"),
			"fieldname": "total_quotations",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Total Sales Orders"),
			"fieldname": "total_sales_orders",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Lead to Opp %"),
			"fieldname": "lead_to_opp_perc",
			"fieldtype": "Percent",
			"width": 120
		},
		{
			"label": _("Opp to Quotation %"),
			"fieldname": "opp_to_quotation_perc",
			"fieldtype": "Percent",
			"width": 140
		}
	]

def get_data(filters):
	data = []
	
	# Get all sales persons (Users who have been assigned a Lead or Opportunity)
	# Joining with User table to get Full Name
	# Adding a filter for Sales Person if selected
	conditions = []
	values = {}
	if filters.get("sales_person"):
		conditions.append("u.name = %(sales_person)s")
		values["sales_person"] = filters.get("sales_person")
	
	condition_str = " AND " + " AND ".join(conditions) if conditions else ""
	
	sales_persons = frappe.db.sql(f"""
		SELECT 
            u.name as user_id, 
            u.full_name as user_name
		FROM `tabLead` l
        JOIN `tabUser` u ON l.custom_assigned_to = u.name
		WHERE l.custom_assigned_to IS NOT NULL AND l.custom_assigned_to != ''
        {condition_str}
        GROUP BY u.name
	""", values, as_dict=1)
	
	for person in sales_persons:
		user = person.user_id
		user_name = person.user_name or user # Fallback to ID if name is empty
		
		# 1. Total Leads
		leads = frappe.get_all("Lead", filters={
			"custom_assigned_to": user,
			"creation": ["between", [filters.get("from_date"), filters.get("to_date")]]
		})
		total_leads = len(leads)
		
		# 2. Total Opportunities
		opps = frappe.get_all("Opportunity", filters={
			"custom_assigned_to": user,
			"creation": ["between", [filters.get("from_date"), filters.get("to_date")]]
		})
		total_opportunities = len(opps)
		
		# 3. Total Quotations
		quotations = frappe.db.get_list("Quotation", filters={
			"opportunity": ["in", [o.name for o in opps]],
			"docstatus": ["<", 2]
		}) if opps else []
		total_quotations = len(quotations)
		
		# 4. Total Sales Orders
		total_sales_orders = 0
		if quotations:
			quotation_names = [q.name for q in quotations]
			total_sales_orders = frappe.db.sql("""
				SELECT COUNT(DISTINCT parent)
				FROM `tabSales Order Item`
				WHERE prevdoc_docname IN %s
				AND docstatus < 2
			""", (quotation_names,))[0][0] or 0
		
		# 5. Ratios
		lead_to_opp_perc = (total_opportunities / total_leads * 100) if total_leads > 0 else 0
		opp_to_quotation_perc = (total_quotations / total_opportunities * 100) if total_opportunities > 0 else 0
		
		data.append({
			"sales_person": user_name, # Display Full Name
			"user_id": user, # Keep ID for reference
			"total_leads": total_leads,
			"total_opportunities": total_opportunities,
			"total_quotations": total_quotations,
			"total_sales_orders": total_sales_orders,
			"lead_to_opp_perc": lead_to_opp_perc,
			"opp_to_quotation_perc": opp_to_quotation_perc
		})
		
	return data

def get_chart(data):
	if not data:
		return None

	labels = [d.get("sales_person") for d in data]
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Total Leads"),
					"values": [d.get("total_leads") for d in data]
				},
				{
					"name": _("Total Opportunities"),
					"values": [d.get("total_opportunities") for d in data]
				},
				{
					"name": _("Total Quotations"),
					"values": [d.get("total_quotations") for d in data]
				}
			]
		},
		"type": "bar",
		"colors": ["#7cd6fd", "#743ee2", "#ff5858"]
	}

def get_report_summary(data):
	if not data:
		return []

	total_leads = sum([d.get("total_leads") for d in data])
	total_opps = sum([d.get("total_opportunities") for d in data])
	total_quotations = sum([d.get("total_quotations") for d in data])

	return [
		{
			"value": total_leads,
			"indicator": "Blue",
			"label": _("Total Leads"),
			"datatype": "Int",
		},
		{
			"value": total_opps,
			"indicator": "Purple",
			"label": _("Total Opportunities"),
			"datatype": "Int",
		},
		{
			"value": total_quotations,
			"indicator": "Red",
			"label": _("Total Quotations"),
			"datatype": "Int",
		}
	]
