import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 115},
        {"label": "Sales Person", "fieldname": "sales_person", "fieldtype": "Data", "width": 130},
        {"label": "Customer ID", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 120},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
        {"label": "Box ID", "fieldname": "box_id", "fieldtype": "Data", "width": 120},
        {"label": "Order Amount", "fieldname": "grand_total", "fieldtype": "Currency", "width": 130, "add_total": 1},
        {"label": "Paid Amount", "fieldname": "allocated_amount", "fieldtype": "Currency", "width": 130, "add_total": 1},
        {"label": "Mode of Payment", "fieldname": "mode_of_payment", "fieldtype": "Data", "width": 180},
        {"label": "Payment Reference", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 140}
    ]

def get_data(filters):
    conditions = "PE.docstatus = 1 AND PER.reference_doctype = 'Sales Order'"
    values = {}
    
    if filters.get("from_date"):
        conditions += " AND PE.posting_date >= %(from_date)s"
        values["from_date"] = filters.get("from_date")
        
    if filters.get("to_date"):
        conditions += " AND PE.posting_date <= %(to_date)s"
        values["to_date"] = filters.get("to_date")
        
    if filters.get("sales_person"):
        conditions += " AND OPP.custom_assigned_to = %(sales_person)s"
        values["sales_person"] = filters.get("sales_person")
        
    if filters.get("customer"):
        conditions += " AND PE.party = %(customer)s"
        values["customer"] = filters.get("customer")
        
    if filters.get("box_id"):
        conditions += " AND OPP.custom_box_id = %(box_id)s"
        values["box_id"] = filters.get("box_id")
        
    if filters.get("mode_of_payment"):
        conditions += " AND PE.mode_of_payment = %(mode_of_payment)s"
        values["mode_of_payment"] = filters.get("mode_of_payment")

    query = f"""
        SELECT 
            PE.posting_date,
            OPP.custom_assigned_full_name AS sales_person,
            PE.party AS customer,
            PE.party_name AS customer_name,
            OPP.custom_box_id AS box_id,
            SO.grand_total,
            PER.allocated_amount,
            PE.mode_of_payment,
            PE.name AS payment_entry
        FROM 
            `tabPayment Entry` PE
        JOIN 
            `tabPayment Entry Reference` PER ON PE.name = PER.parent
        JOIN 
            `tabSales Order` SO ON PER.reference_name = SO.name
        JOIN 
            `tabSales Order Item` SOI ON SO.name = SOI.parent
        JOIN 
            `tabQuotation` QT ON SOI.prevdoc_docname = QT.name
        JOIN 
            `tabOpportunity` OPP ON QT.opportunity = OPP.name
        WHERE 
            {conditions}
        GROUP BY 
            PE.name, PER.name
        ORDER BY 
            PE.posting_date DESC
    """
    
    return frappe.db.sql(query, values, as_dict=True)
