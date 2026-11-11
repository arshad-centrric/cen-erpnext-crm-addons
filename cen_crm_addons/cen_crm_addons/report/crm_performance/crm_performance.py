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
			"width": 160,
			"hidden": 1
		},
		{
			"label": _("Opp to Sales Order %"),
			"fieldname": "opp_to_so_percent",
			"fieldtype": "Percent",
			"width": 180
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
	
	# Payments are collected against the Sales Order first and, once it is invoiced, against the Sales Invoice.
	# Trace both back to the Opportunity (via the Quotation the order was made from) so each payment row
	# is counted once, whichever document it was allocated to:
	# Payment Entry Reference -> Sales Order / Sales Invoice -> Quotation -> Opportunity -> Sales Person
	validate_branch_company(filters)
	opportunity_filters = get_opportunity_filters(filters)
	branch_users = get_branch_users(filters.get("branch"))

	payments_query = """
		SELECT
			opt.custom_assigned_to as user_id,
			SUM(payment.amount) as amount
		FROM (
			SELECT
				per.allocated_amount AS amount,
				CASE per.reference_doctype
					WHEN 'Sales Order' THEN (
						SELECT MIN(qt.opportunity)
						FROM `tabSales Order Item` soi
						JOIN `tabQuotation` qt ON qt.name = soi.prevdoc_docname
						WHERE soi.parent = per.reference_name
					)
					ELSE (
						SELECT MIN(qt.opportunity)
						FROM `tabSales Invoice Item` sii
						JOIN `tabSales Order Item` soi ON soi.parent = sii.sales_order
						JOIN `tabQuotation` qt ON qt.name = soi.prevdoc_docname
						WHERE sii.parent = per.reference_name
					)
				END AS opportunity
			FROM
				`tabPayment Entry` pe
			JOIN
				`tabPayment Entry Reference` per ON pe.name = per.parent
			WHERE
				pe.docstatus = 1
				AND pe.payment_type = 'Receive'
				AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
				AND (
					per.reference_doctype = 'Sales Order'
					OR (
						per.reference_doctype = 'Sales Invoice'
						AND EXISTS (
							SELECT 1 FROM `tabSales Invoice` si WHERE si.name = per.reference_name AND si.docstatus = 1
						)
					)
				)
		) payment
		JOIN
			`tabOpportunity` opt ON payment.opportunity = opt.name
		WHERE
			1 = 1
			{opportunity_conditions}
		GROUP BY
			opt.custom_assigned_to
	"""
	opportunity_conditions = ""
	if filters.get("company"):
		opportunity_conditions += " AND opt.company = %(company)s"
	if filters.get("branch"):
		# Records made before branches were rolled out have none; they belong to their assignee's branch
		opportunity_conditions += """ AND (
			opt.custom_cen_branch = %(branch)s
			OR (IFNULL(opt.custom_cen_branch, '') = '' AND opt.custom_assigned_to IN (
				SELECT user FROM `tabBranch User` WHERE parent = %(branch)s
			))
		)"""
	payments_list = frappe.db.sql(
		payments_query.format(opportunity_conditions=opportunity_conditions), filters, as_dict=True
	)
	payments_map = {p.user_id: p.amount for p in payments_list}

	# REVERTED DISCOVERY LOGIC: JOIN ON tabLead
	conditions = []
	values = {}
	if filters.get("sales_person"):
		conditions.append("u.name = %(sales_person)s")
		values["sales_person"] = filters.get("sales_person")
	
	condition_str = " AND " + " AND ".join(conditions) if conditions else ""
	
	# Restoring the grouping by Lead assignment to ensure existing data is found
	if filters.get("company") or filters.get("branch"):
		# Narrowed to a company or branch: list the users who have opportunities there in the period,
		# plus anyone paid in the period on an earlier opportunity there
		sales_persons = get_sales_persons_with_opportunities(
			filters, opportunity_filters, branch_users, extra_users=set(payments_map)
		)
	else:
		sales_persons = get_sales_persons_from_leads(condition_str, values)

	for person in sales_persons:
		user = person.user_id
		user_name = person.user_name or user
		
		# 1. Total Opportunities (Restoring get_all for stability)
		opps = get_user_opportunities(user, filters, opportunity_filters, branch_users)
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
		opp_to_so_percent = (total_sales_orders / total_opportunities * 100) if total_opportunities > 0 else 0
		
		data.append({
			"sales_person": user_name,
			"user_id": user,
			"total_opportunities": total_opportunities,
			"total_quotations": total_quotations,
			"total_sales_orders": total_sales_orders,
			"total_payments_received": total_payments,
			"opp_to_quotation_perc": opp_to_quotation_perc,
			"opp_to_so_percent": opp_to_so_percent
		})
		
	return data

def validate_branch_company(filters):
	if filters.get("company") and filters.get("branch"):
		branch_company = frappe.db.get_value("Branch", filters.get("branch"), "custom_cen_default_company")
		if branch_company != filters.get("company"):
			frappe.throw(_("Branch {0} does not belong to company {1}").format(filters.get("branch"), filters.get("company")))

def get_opportunity_filters(filters):
	"""Company condition shared by every Opportunity lookup in this report."""
	opportunity_filters = {}
	if filters.get("company"):
		opportunity_filters["company"] = filters.get("company")
	return opportunity_filters

def get_branch_users(branch):
	if not branch:
		return set()
	return set(frappe.get_all("Branch User", filters={"parent": branch}, pluck="user"))

def get_user_opportunities(user, filters, opportunity_filters, branch_users):
	"""Opportunities assigned to the user in the period, narrowed to the company and branch filters."""
	query_filters = {
		"custom_assigned_to": user,
		"creation": ["between", [filters.get("from_date"), filters.get("to_date")]],
		**opportunity_filters
	}
	or_filters = None
	branch = filters.get("branch")
	if branch:
		if user in branch_users:
			# Records made before branches were rolled out have none; they belong to the assignee's branch
			or_filters = [["custom_cen_branch", "=", branch], ["custom_cen_branch", "is", "not set"]]
		else:
			query_filters["custom_cen_branch"] = branch
	return frappe.get_all("Opportunity", filters=query_filters, or_filters=or_filters)

def get_sales_persons_from_leads(condition_str, values):
	return frappe.db.sql(f"""
		SELECT 
            u.name as user_id, 
            u.full_name as user_name
		FROM `tabLead` l
        JOIN `tabUser` u ON l.custom_assigned_to = u.name
		WHERE l.custom_assigned_to IS NOT NULL AND l.custom_assigned_to != ''
        {condition_str}
        GROUP BY u.name
	""", values, as_dict=1)

def get_sales_persons_with_opportunities(filters, opportunity_filters, branch_users, extra_users=()):
	opps = frappe.get_all(
		"Opportunity",
		filters={
			"creation": ["between", [filters.get("from_date"), filters.get("to_date")]],
			"custom_assigned_to": ["is", "set"],
			**opportunity_filters,
		},
		fields=["custom_assigned_to", "custom_cen_branch"],
	)
	branch = filters.get("branch")
	if branch:
		opps = [
			o for o in opps
			if o.custom_cen_branch == branch or (not o.custom_cen_branch and o.custom_assigned_to in branch_users)
		]
	users = {o.custom_assigned_to for o in opps} | set(extra_users)
	if filters.get("sales_person"):
		users &= {filters.get("sales_person")}
	if not users:
		return []
	return frappe.get_all(
		"User",
		filters={"name": ["in", list(users)]},
		fields=["name as user_id", "full_name as user_name"],
		order_by="full_name asc",
	)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_sales_users(doctype, txt, searchfield, start, page_len, filters):
	filters = frappe.parse_json(filters) if filters else {}
	company = filters.get("company")
	branch = filters.get("branch")

	if branch or company:
		# Narrowed to a branch (or every branch of a company): the users assigned to it
		condition = "bu.parent = %(branch)s" if branch else "b.custom_cen_default_company = %(company)s"
		return frappe.db.sql(f"""
			SELECT DISTINCT
				u.name, u.full_name
			FROM
				`tabUser` u
			JOIN
				`tabBranch User` bu ON bu.user = u.name
			JOIN
				`tabBranch` b ON b.name = bu.parent
			WHERE
				u.enabled = 1
				AND {condition}
				AND (u.name LIKE %(txt)s OR u.full_name LIKE %(txt)s)
			ORDER BY
				u.full_name ASC
			LIMIT %(start)s, %(page_len)s
		""", {
			"branch": branch,
			"company": company,
			"txt": f"%%{txt}%%",
			"start": start,
			"page_len": page_len
		})

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
	
	total_company_opps = sum(row.get("total_opportunities", 0) for row in data)
	total_company_sos = sum(row.get("total_sales_orders", 0) for row in data)
	company_yield = (total_company_sos / total_company_opps * 100) if total_company_opps > 0 else 0

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
			"value": company_yield,
			"indicator": "Blue",
			"label": _("Opportunity to Sales Order %"),
			"datatype": "Percent",
		},
		{
			"value": total_payments,
			"indicator": "Green",
			"label": _("Total Company Revenue"),
			"datatype": "Currency",
		}
	]
