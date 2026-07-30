import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe import _

@frappe.whitelist()
def get_delivery_list(status="Pending", limit_start=1, limit_page_length=20, search_term="", warehouse=""):
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
    
    # Warehouse Filter
    if warehouse:
        conditions.append("so.set_warehouse = %(warehouse)s")
        values["warehouse"] = warehouse

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