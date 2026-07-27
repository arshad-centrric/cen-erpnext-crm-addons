import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from frappe.utils.file_manager import save_file

@frappe.whitelist()
def get_packing_orders(status="Pending", limit_start=1, limit_page_length=10, search_term=None, warehouse=None):
    """
    Fetch a paginated list of Sales Orders based on packing status.
    status: 'Pending' (maps to 'Assigned to Pack') or 'Completed' (maps to 'Packed')
    limit_start: Page number, defaults to 1
    limit_page_length: Number of items per page, defaults to 10
    search_term: Optional string to search across name, customer, customer_name
    warehouse: Optional string to filter by warehouse
    """
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 10
    
    status_lower = (status or "").strip().lower()
    
    if status_lower == "pending":
        picking_status = "Assigned to Pack"
        order_by = "delivery_date ASC, custom_delivery_time ASC"
    elif status_lower == "completed":
        picking_status = "Packed"
        order_by = "modified DESC"
    else:
        return []

    filters = {
        "docstatus": 1,
        "custom_picking_status": picking_status
    }
    
    if warehouse:
        filters["set_warehouse"] = warehouse

    or_filters = {}
    if search_term:
        or_filters = {
            "name": ["like", f"%{search_term}%"],
            "customer": ["like", f"%{search_term}%"],
            "customer_name": ["like", f"%{search_term}%"]
        }

    orders = frappe.get_all(
        "Sales Order",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", 
            "customer", 
            "customer_name", 
            "transaction_date", 
            "delivery_date", 
            "custom_delivery_time", 
            "custom_picking_status", 
            "status", 
            "grand_total",
            "set_warehouse"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by=order_by
    )
    
    return orders


@frappe.whitelist()
def mark_order_as_packed(sales_order, packing_image_url=None, submit=0):
    """
    Update Sales Order as Packed, fill custom packing image (using a pre-uploaded file URL), 
    and create a Sales Invoice auto-fetching the existing Box ID.
    If 'submit' is passed as 1, it will also submit the created Sales Invoice.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required")
        
    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} not found", frappe.DoesNotExistError)
        
    # Fetch the existing Box ID directly from the Sales Order
    existing_box_id = frappe.db.get_value("Sales Order", sales_order, "custom_box_id")
        
    # Prepare updates for the Sales Order
    so_updates = {
        "custom_picking_status": "Packed"
    }
    
    # Directly assign the URL passed from your frontend/upload API
    if packing_image_url:
        so_updates["custom_packing_image"] = str(packing_image_url).strip()

    # Apply all updates to the Sales Order
    frappe.db.set_value("Sales Order", sales_order, so_updates)
    
    # Automatically generate the Sales Invoice
    try:
        si_doc = make_sales_invoice(sales_order)
        
        # Push the fetched Box ID into the Sales Invoice
        if existing_box_id:
            si_doc.custom_box_id = existing_box_id
            
        # Auto-allocate advances if submitting
        from frappe.utils import cint
        if cint(submit) == 1:
            si_doc.allocate_advances_automatically = 1
            si_doc.set_advances()
            
        # Insert (save as Draft)
        si_doc.insert()
        
        # Submit if requested
        if cint(submit) == 1:
            si_doc.submit()
        
    except Exception as e:
        frappe.log_error(title="Auto Sales Invoice Creation Failed", message=frappe.get_traceback())
        frappe.throw(f"Sales Order was updated, but failed to create Sales Invoice: {str(e)}")
    
    return {
        "status": "success", 
        "message": f"Sales Order {sales_order} marked as Packed and Sales Invoice {si_doc.name} created.",
        "data": {
            "sales_order": sales_order,
            "sales_invoice": si_doc.name,
            "box_id": existing_box_id,
            "packing_image": packing_image_url
        }
    }


@frappe.whitelist()
def update_packing_details(sales_order, picking_status=None, packing_instructions=None):
    """
    Dynamically update Sales Order packing status and/or packing instructions 
    depending on what fields are provided in the payload.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required")
        
    if not frappe.db.exists("Sales Order", sales_order):
        frappe.throw(f"Sales Order {sales_order} not found", frappe.DoesNotExistError)
        
    # Initialize an empty dictionary for fields to update
    so_updates = {}
    
    # If picking_status is passed in the payload, add it to updates
    if picking_status:
        so_updates["custom_picking_status"] = str(picking_status).strip()
        
    # If packing_instructions is passed in the payload, add it to updates
    if packing_instructions is not None:  # Using 'is not None' to allow clearing text if needed
        so_updates["custom_packing_instructions"] = str(packing_instructions).strip()
        
    # If nothing to update, return early
    if not so_updates:
        frappe.throw("No fields provided to update")
        
    # Apply the dynamic updates to the Sales Order database record
    frappe.db.set_value("Sales Order", sales_order, so_updates)
    
    return {
        "status": "success", 
        "message": f"Sales Order {sales_order} has been updated successfully.",
        "data": {
            "sales_order": sales_order,
            **so_updates
        }
    }