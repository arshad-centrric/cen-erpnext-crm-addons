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
			"label": _("Total Opportunities"),
			"fieldname": "total_opportunities",
			"fieldtype": "Int",
			"width": 160
		},
		{
			"label": _("Total Quotations"),
			"fieldname": "total_quotations",
			"fieldtype": "Int",
			"width": 150
		},
		{
			"label": _("Total Sales Orders"),
			"fieldname": "total_sales_orders",
			"fieldtype": "Int",
			"width": 150
		},
		{
			"label": _("Opp to Quotation %"),
			"fieldname": "opp_to_quotation_perc",
			"fieldtype": "Percent",
			"width": 160
		},
		{
			"label": _("Total Payments Received"),
			"fieldname": "total_payments_received",
			"fieldtype": "Currency",
			"width": 220
		}
	]

def get_data(filters):
	data = []
	
	# High-performance trace: 
	# Payment Entry Reference -> Sales Order Item -> Quotation -> Opportunity -> Sales Person
	payments_query = """
		SELECT
			opt.custom_assigned_to as user_id,
			SUM(per.allocated_amount) as amount
		FROM
			`tabPayment Entry` pe
		JOIN
			`tabPayment Entry Reference` per ON pe.name = per.parent
		JOIN
			`tabSales Order Item` soi ON per.reference_name = soi.parent
		JOIN
			`tabQuotation` qt ON soi.prevdoc_docname = qt.name
		JOIN
			`tabOpportunity` opt ON qt.opportunity = opt.name
		WHERE
			pe.docstatus = 1
			AND per.reference_doctype = 'Sales Order'
			AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY
			opt.custom_assigned_to
	"""
	payments_list = frappe.db.sql(payments_query, filters, as_dict=True)
	payments_map = {p.user_id: p.amount for p in payments_list}

	# REVERTED DISCOVERY LOGIC: JOIN ON tabLead
	conditions = []
	values = {}
	if filters.get("sales_person"):
		conditions.append("u.name = %(sales_person)s")
		values["sales_person"] = filters.get("sales_person")
	
	condition_str = " AND " + " AND ".join(conditions) if conditions else ""
	
	# Restoring the grouping by Lead assignment to ensure existing data is found
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
		user_name = person.user_name or user
		
		# 1. Total Opportunities (Restoring get_all for stability)
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
		
		# 5. Total Payments
		total_payments = payments_map.get(user, 0)
		
		# 6. Ratios
		opp_to_quotation_perc = (total_quotations / total_opportunities * 100) if total_opportunities > 0 else 0
		
		data.append({
			"sales_person": user_name,
			"user_id": user,
			"total_opportunities": total_opportunities,
			"total_quotations": total_quotations,
			"total_sales_orders": total_sales_orders,
			"total_payments_received": total_payments,
			"opp_to_quotation_perc": opp_to_quotation_perc
		})
		
	return data

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_sales_users(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql("""
		SELECT 
            u.name, u.full_name
		FROM 
            `tabUser` u
		JOIN 
            `tabHas Role` hr ON u.name = hr.parent
		WHERE 
            hr.role = 'Sales Person'
            AND u.enabled = 1
            AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
		ORDER BY 
            u.full_name ASC
		LIMIT %(start)s, %(page_len)s
	""", {
		"txt": f"%%{txt}%%",
		"start": start,
		"page_len": page_len
	})

def get_chart(data):
	if not data:
		return None

	labels = [d.get("sales_person") for d in data]
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
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
		"colors": ["#743ee2", "#ff5858"]
	}

def get_report_summary(data):
	if not data:
		return []

	total_opps = sum([d.get("total_opportunities") for d in data])
	total_quotations = sum([d.get("total_quotations") for d in data])
	total_payments = sum([d.get("total_payments_received") for d in data])

	return [
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
		},
		{
			"value": total_payments,
			"indicator": "Green",
			"label": _("Total Company Revenue"),
			"datatype": "Currency",
		}
	]
