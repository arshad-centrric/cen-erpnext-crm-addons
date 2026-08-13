import frappe
import json
from frappe.utils import cint, flt

@frappe.whitelist()
def get_goods_receipt_notes(status="Draft", search_term=None, limit_start=1, limit_page_length=10, warehouse=None, company=None, date=None):
    """
    Fetch a paginated list of Goods Receipt Notes (Purchase Receipts) with an optional search.
    status: 'Draft' (docstatus 0), 'Submitted' (docstatus 1), or 'Cancelled' (docstatus 2)
    search_term: String to search by PR number, supplier, or supplier name
    limit_start: Page number, defaults to 1
    limit_page_length: Number of items per page, defaults to 10
    warehouse: Optional string to filter by accepted warehouse
    """
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 10
        
    status_lower = (status or "").strip().lower()
    
    if status_lower == "draft":
        docstatus = 0
    elif status_lower == "submitted":
        docstatus = 1
    elif status_lower == "cancelled":
        docstatus = 2
    else:
        return []

    # Base filters (AND conditions)
    filters = {
        "docstatus": docstatus
    }
    
    if warehouse:
        filters["set_warehouse"] = str(warehouse).strip()
        
    if company:
        filters["company"] = str(company).strip()
    
    if date:
        filters["posting_date"] = date
    
    # Optional search filters (OR conditions)
    or_filters = {}
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "name": ["like", search_string],
            "supplier": ["like", search_string],
            "supplier_name": ["like", search_string]
        }

    grns = frappe.get_all(
        "Purchase Receipt",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name", 
            "supplier", 
            "supplier_name", 
            "posting_date", 
            "posting_time", 
            "company", 
            "status", 
            "grand_total",
            "set_warehouse"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="modified DESC"
    )
    
    return grns


@frappe.whitelist()
def get_suppliers(search_term=None, limit_start=1, limit_page_length=20):
    """
    Fetch a paginated list of active Suppliers with an optional search.
    search_term: String to search by supplier ID (name) or supplier_name
    limit_start: Page number, defaults to 1
    limit_page_length: Number of items per page, defaults to 20
    """
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    # Base filters (exclude disabled suppliers)
    filters = {
        "disabled": 0
    }

    # Optional search filters (OR conditions)
    or_filters = {}
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "name": ["like", search_string],
            "supplier_name": ["like", search_string]
        }

    suppliers = frappe.get_all(
        "Supplier",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "supplier_name",
            "supplier_type",
            "mobile_no",
            "email_id"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="supplier_name ASC"
    )

    return suppliers

@frappe.whitelist()
def create_supplier(supplier_name, supplier_type, supplier_group="All Supplier Groups", mobile_no=None, email_id=None):
    """
    Create a new Supplier.
    supplier_name: Name of the Supplier (Required)
    supplier_type: Type of supplier ('Company', 'Individual', 'Partnership') (Required)
    supplier_group: Supplier Group (Defaults to 'All Supplier Groups')
    mobile_no: Contact number (Optional)
    email_id: Email address (Optional)
    """
    if not supplier_name:
        frappe.throw("Supplier Name is a required parameter")

    if not supplier_type:
        frappe.throw("Supplier Type is a required parameter")

    # Validate against the dropdown options shown in your ERPNext instance
    valid_supplier_types = ["Company", "Individual", "Partnership"]
    if str(supplier_type).strip() not in valid_supplier_types:
        frappe.throw(f"Invalid Supplier Type. Must be one of: {', '.join(valid_supplier_types)}")

    # Check if the supplier already exists to prevent duplicate errors
    if frappe.db.exists("Supplier", {"supplier_name": supplier_name}):
        frappe.throw(f"A Supplier with the name '{supplier_name}' already exists.")

    try:
        # Initialize the new Supplier document
        supplier_doc = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": str(supplier_name).strip(),
            "supplier_group": str(supplier_group).strip(),
            "supplier_type": str(supplier_type).strip()
        })

        # Set optional fields if they are provided
        if mobile_no:
            supplier_doc.mobile_no = str(mobile_no).strip()
        if email_id:
            supplier_doc.email_id = str(email_id).strip()

        # Insert the document into the database
        supplier_doc.insert()

        return {
            "status": "success",
            "message": f"Supplier {supplier_doc.name} has been created.",
            "data": {
                "name": supplier_doc.name,
                "supplier_name": supplier_doc.supplier_name,
                "supplier_group": supplier_doc.supplier_group,
                "supplier_type": supplier_doc.supplier_type,
                "mobile_no": supplier_doc.mobile_no,
                "email_id": supplier_doc.email_id
            }
        }

    except Exception as e:
        # Log the exact error for debugging
        frappe.log_error(title="Supplier Creation API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to create Supplier: {str(e)}")

@frappe.whitelist()
def get_purchase_receipt_details(receipt_id):
    """
    Fetch the complete details of a specific Purchase Receipt, including items.
    receipt_id: The exact name (ID) of the Purchase Receipt (e.g., 'MAT-PRE-2023-00001')
    """
    if not receipt_id:
        frappe.throw("Parameter 'receipt_id' is required")

    # Check if it exists before trying to fetch
    if not frappe.db.exists("Purchase Receipt", receipt_id):
        frappe.throw(f"Purchase Receipt '{receipt_id}' not found", frappe.DoesNotExistError)

    try:
        # Get the full document
        doc = frappe.get_doc("Purchase Receipt", receipt_id)
        doc_data = doc.as_dict()
        
        # Fetch Attachments
        attachments = frappe.get_all(
            "File", 
            filters={"attached_to_doctype": "Purchase Receipt", "attached_to_name": receipt_id}, 
            fields=["name", "file_name", "file_url"]
        )
        doc_data["attachments"] = attachments
        
        # Return it as a dictionary (this automatically includes the 'items' child table)
        return {
            "status": "success",
            "data": doc_data
        }

    except Exception as e:
        frappe.log_error(title="Fetch Purchase Receipt API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to fetch details: {str(e)}")

@frappe.whitelist()
def create_purchase_receipt(supplier=None, company=None, items=None, accepted_warehouse=None, supplier_delivery_note=None, submit=0):
    """
    Create a new Purchase Receipt.
    supplier: Exact name of the Supplier (Required)
    company: Exact name of the Company (Optional, defaults to Global/User default)
    accepted_warehouse: The default warehouse for all items (Required)
    items: JSON string or list of dicts containing item_code, qty, rate, uom (Required)
    supplier_delivery_note: Delivery note number provided by the supplier (Optional)
    submit: 1 to submit immediately, 0 to leave as Draft
    """
    if not supplier or not accepted_warehouse or not items:
        frappe.throw("Supplier, Accepted Warehouse, and Items are required parameters")

    if not company:
        # Auto-detect the company from the provided warehouse
        if accepted_warehouse:
            company = frappe.db.get_value("Warehouse", accepted_warehouse, "company")
            
        # Fallback to default if somehow the warehouse has no company linked
        if not company:
            company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company")
            
        if not company:
            frappe.throw("Company is required and no default company found")

    # If calling via REST, 'items' often comes through as a JSON string
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw("Invalid JSON format for items payload")

    if not isinstance(items, list) or len(items) == 0:
        frappe.throw("Items must be a non-empty list", frappe.ValidationError)

    try:
        # Initialize the base document arguments
        doc_args = {
            "doctype": "Purchase Receipt",
            "supplier": str(supplier).strip(),
            "company": str(company).strip(),
            "set_warehouse": str(accepted_warehouse).strip() # Sets the parent-level Accepted Warehouse
        }

        # Add the optional supplier delivery note if provided
        if supplier_delivery_note:
            doc_args["supplier_delivery_note"] = str(supplier_delivery_note).strip()

        # Create the document instance
        pr_doc = frappe.get_doc(doc_args)

        # Append items to the child table
        for item in items:
            if not item.get("item_code") or not item.get("qty"):
                frappe.throw("Each item must contain at least an 'item_code' and 'qty'")
                
            row_data = {
                "item_code": item.get("item_code"),
                "qty": flt(item.get("qty")),
                "warehouse": str(accepted_warehouse).strip(), # Assign the general warehouse to the item row
                "rate": flt(item.get("rate")) if item.get("rate") else 0.0
            }
            
            if item.get("uom"):
                row_data["uom"] = str(item.get("uom")).strip()
                
            pr_doc.append("items", row_data)

        # Insert the document (creates it as Draft)
        pr_doc.flags.ignore_permissions = True
        pr_doc.insert(ignore_permissions=True)

        # Submit if requested
        if cint(submit) == 1:
            pr_doc.submit()

        return {
            "status": "success", 
            "message": f"Purchase Receipt {pr_doc.name} has been created.",
            "data": {
                "name": pr_doc.name,
                "docstatus": pr_doc.docstatus,
                "supplier_delivery_note": pr_doc.supplier_delivery_note,
                "accepted_warehouse": pr_doc.set_warehouse
            }
        }

    except Exception as e:
        # Log the error in Frappe's Error Log for easier debugging
        frappe.log_error(title="Purchase Receipt Creation API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to create Purchase Receipt: {str(e)}")