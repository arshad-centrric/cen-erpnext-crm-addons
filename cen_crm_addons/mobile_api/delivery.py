import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe import _

@frappe.whitelist()
def get_delivery_list(status="Pending", limit_start=1, limit_page_length=20, search_term="", warehouse="", company="", delivery_date=None, mode_of_delivery=None, branch=None):
    # Convert frontend's 1-based index to SQL's 0-based OFFSET
    frontend_start = int(limit_start)
    sql_offset = max(0, frontend_start - 1)
    
    limit_page_length = int(limit_page_length)

    # Base conditions
    conditions = ["so.docstatus = 1"]
    values = {
        "limit_start": sql_offset,
        "limit_page_length": limit_page_length
    }
    
    resolved_branch = branch or frappe.defaults.get_user_default("branch")
    
    # Warehouse Filter
    if warehouse and str(warehouse).strip():
        conditions.append("so.set_warehouse = %(warehouse)s")
        values["warehouse"] = str(warehouse).strip()
        
    if resolved_branch and str(resolved_branch).strip() and resolved_branch != "All Branches":
        conditions.append("so.branch = %(branch)s")
        values["branch"] = str(resolved_branch).strip()
        
    # Company Filter
    if company:
        conditions.append("so.company = %(company)s")
        values["company"] = company

    if delivery_date:
        conditions.append("so.delivery_date = %(delivery_date)s")
        values["delivery_date"] = delivery_date

    if mode_of_delivery:
        conditions.append("so.custom_mode_of_delivery = %(mode_of_delivery)s")
        values["mode_of_delivery"] = mode_of_delivery

    # Tab-specific logic
    if status == "Pending":
        conditions.append("so.custom_picking_status = 'Packed'")
        # Strictly filter out fully delivered items
        conditions.append("so.delivery_status != 'Fully Delivered'")
        
        
        order_by = "so.delivery_date ASC, so.custom_delivery_time ASC"
    else:
        # Completed Tab logic
        conditions.append("so.delivery_status = 'Fully Delivered'")
        order_by = "so.modified DESC"

    # Search logic
    if search_term:
        # Use partial match (LIKE) for all fields including SO ID
        conditions.append("""(
            so.name LIKE %(search_like)s OR 
            so.custom_box_id LIKE %(search_like)s OR 
            so.customer LIKE %(search_like)s OR 
            so.customer_name LIKE %(search_like)s
        )""")
        values['search_like'] = f"%{search_term}%"

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT 
            so.name as sales_order_id,
            so.customer,
            so.customer_name,
            so.status as sales_order_status,
            so.delivery_status,
            so.set_warehouse as source_warehouse,
            so.custom_mode_of_delivery,
            so.delivery_date,
            so.custom_delivery_time,
            so.custom_delivery_contact,
            so.custom_box_id,
            so.branch,
            CASE 
                WHEN so.custom_payment_status = 'Paid' OR so.advance_paid >= so.grand_total THEN 'Paid'
                WHEN so.advance_paid > 0 AND so.advance_paid < so.grand_total THEN 'Partially Paid'
                ELSE 'Unpaid'
            END as payment_status,
            so.grand_total,
            (so.grand_total - so.advance_paid) as pending_amount
        FROM `tabSales Order` so
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT %(limit_page_length)s OFFSET %(limit_start)s
    """
    
    return frappe.db.sql(query, values, as_dict=True)


@frappe.whitelist()
def submit_delivery(sales_order):
    try:
        # 1. State Protection: Validate existence and status
        if not frappe.db.exists("Sales Order", sales_order):
            frappe.throw(_("Sales Order {0} not found.").format(sales_order))
            
        so_data = frappe.db.get_value("Sales Order", sales_order, ["docstatus", "delivery_status"], as_dict=True)
        
        if so_data.docstatus != 1:
            frappe.throw(_("Sales Order {0} must be submitted before delivery.").format(sales_order))
            
        if so_data.delivery_status == "Fully Delivered":
            frappe.throw(_("Sales Order {0} is already fully delivered.").format(sales_order))

        # 2. Native Mapping: Generate the Delivery Note from the SO
        dn_doc = make_delivery_note(sales_order)
        
        fetched_branch = frappe.db.get_value("Sales Order", sales_order, "branch") or frappe.db.get_value("Sales Order", sales_order, "custom_cen_branch")
        if fetched_branch:
            dn_doc.branch = fetched_branch
        
        # 3. Save and Submit
        dn_doc.insert(ignore_permissions=True)
        dn_doc.submit()

        # NOTE: Placeholder for Draft Sales Invoice submission.
        # If Sakeer decides the Draft SI should be submitted at this exact moment,
        # we will add the logic to fetch and submit it right here.

        return {
            "status": "success",
            "message": "Delivery Note created and submitted successfully.",
            "delivery_note_id": dn_doc.name
        }

    except Exception as e:
        # Log the full error in Frappe's Error Log list for easy debugging
        frappe.log_error(frappe.get_traceback(), f"Mobile API: Delivery Submission Failed - {sales_order}")
        return {
            "status": "error",
            "message": str(e)
        }


@frappe.whitelist()
def get_delivery_order_details(sales_order):
    """
    Fetch full details of a specific Sales Order for the delivery tab,
    strictly enforcing the physical packing status guard.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required")
        
    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} not found", frappe.DoesNotExistError)
        
    doc = frappe.get_doc("Sales Order", sales_order)
    
    if doc.custom_picking_status != "Packed":
        frappe.throw(f"This Sales Order has not been packed yet. Current Status: {doc.custom_picking_status or 'Pending'}")
    
    # Convert document to dictionary
    order_details = doc.as_dict()
    
    # Dynamic outstanding calculation: check if there is an active Sales Invoice
    active_si = frappe.db.sql("""
        SELECT si.name, si.outstanding_amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus = 1
        LIMIT 1
    """, (sales_order,), as_dict=True)
    
    if active_si:
        outstanding = flt(active_si[0].outstanding_amount)
        has_active_invoice = 1
        order_details["active_invoice"] = active_si[0].name
    else:
        grand_total = flt(order_details.get("grand_total", 0.0))
        advance_amount = flt(order_details.get("advance_paid", order_details.get("advance_amount", 0.0)))
        outstanding = grand_total - advance_amount
        has_active_invoice = 0
        order_details["active_invoice"] = None
        
    order_details["pending_amount"] = outstanding
    order_details["outstanding_amount"] = outstanding
    order_details["has_active_invoice"] = has_active_invoice
    
    # Fetch all non-cancelled linked Sales Invoices
    linked_sales_invoices = frappe.db.sql("""
        SELECT DISTINCT si.name, si.docstatus, si.status
        FROM `tabSales Invoice` si
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
        WHERE sii.sales_order = %s AND si.docstatus != 2
    """, (sales_order,), as_dict=True)
    
    order_details["linked_sales_invoices"] = linked_sales_invoices
    
    return order_details