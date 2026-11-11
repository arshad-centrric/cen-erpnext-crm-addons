import frappe
import json
from frappe.utils import cint, flt
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt as make_receipt_from_po
from erpnext.stock.get_item_details import get_conversion_factor

from cen_crm_addons.api.purchase_receipt_hooks import RECEIVABLE_PO_STATUSES

@frappe.whitelist()
def get_goods_receipt_notes(status="Draft", search_term=None, limit_start=1, limit_page_length=10, warehouse=None, company=None, date=None, branch=None):
    """
    Fetch a paginated list of Goods Receipt Notes (Purchase Receipts) with an optional search.
    status: 'Draft' (docstatus 0), 'Submitted' (docstatus 1), or 'Cancelled' (docstatus 2)
    search_term: String to search by PR number, supplier, or supplier name
    limit_start: Page number, defaults to 1
    limit_page_length: Number of items per page, defaults to 10
    warehouse: Optional string to filter by accepted warehouse
    """
    resolved_branch = branch or frappe.defaults.get_user_default("branch")
    
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
    
    if warehouse and str(warehouse).strip():
        filters["set_warehouse"] = str(warehouse).strip()
        
    if company:
        filters["company"] = str(company).strip()
    
    if date:
        filters["posting_date"] = date
        
    if resolved_branch and str(resolved_branch).strip() and resolved_branch != "All Branches":
        filters["branch"] = str(resolved_branch).strip()
    
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
            "set_warehouse",
            "branch",
            "custom_purchase_order"
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
def get_supplier_purchase_orders(supplier, company=None, search_term=None, limit_start=1, limit_page_length=20):
    """
    Fetch the submitted Purchase Orders of a Supplier that can still be received
    (status 'To Receive and Bill'). Used for the Purchase Order dropdown when creating a GRN.
    supplier: Exact name of the Supplier (Required)
    company: Optional company filter
    search_term: Optional search on PO number
    limit_start: Page number, defaults to 1
    limit_page_length: Number of items per page, defaults to 20
    """
    if not supplier:
        frappe.throw("Supplier is a required parameter")

    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    filters = {
        "supplier": str(supplier).strip(),
        "docstatus": 1,
        "status": ["in", RECEIVABLE_PO_STATUSES]
    }

    if company:
        filters["company"] = str(company).strip()

    if search_term:
        filters["name"] = ["like", f"%{str(search_term).strip()}%"]

    return frappe.get_all(
        "Purchase Order",
        filters=filters,
        fields=[
            "name",
            "supplier",
            "supplier_name",
            "transaction_date",
            "schedule_date",
            "company",
            "status",
            "set_warehouse",
            "grand_total",
            "per_received",
            "per_billed"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="transaction_date DESC, name DESC"
    )


@frappe.whitelist()
def get_purchase_order_pending_items(purchase_order):
    """
    Fetch a Purchase Order's items that are still pending to be received,
    so the mobile app can pre-fill the GRN items.
    purchase_order: Exact name of the Purchase Order (Required)

    Send each row's 'purchase_order_item' back in create_purchase_receipt's items
    so the GRN row is linked to the exact PO row.
    """
    if not purchase_order:
        frappe.throw("Parameter 'purchase_order' is required")

    if not frappe.db.exists("Purchase Order", purchase_order):
        frappe.throw(f"Purchase Order '{purchase_order}' not found", frappe.DoesNotExistError)

    # Reuse ERPNext's own PO -> PR mapping so pending qty matches the web exactly
    mapped = make_receipt_from_po(purchase_order)

    items = [
        {
            "purchase_order_item": row.purchase_order_item,
            "item_code": row.item_code,
            "item_name": row.item_name,
            "uom": row.uom,
            "stock_uom": row.stock_uom,
            "conversion_factor": row.conversion_factor,
            "pending_qty": flt(row.qty),
            "rate": flt(row.rate),
            "warehouse": row.warehouse
        }
        for row in mapped.get("items")
    ]

    return {
        "status": "success",
        "data": {
            "purchase_order": purchase_order,
            "supplier": mapped.supplier,
            "company": mapped.company,
            "set_warehouse": mapped.set_warehouse,
            "items": items
        }
    }


def _build_receipt_from_purchase_order(purchase_order, supplier, company, items, accepted_warehouse):
    """
    Build a Purchase Receipt from a Purchase Order using ERPNext's mapper, so every
    row carries purchase_order / purchase_order_item (same link the web creates).
    Only the items sent by the app are kept, with the app's qty / rate / uom.
    Items sent that are not on the PO are added as normal, unlinked rows.
    """
    po = frappe.db.get_value(
        "Purchase Order", purchase_order, ["supplier", "company", "docstatus", "status"], as_dict=True
    )
    if not po:
        frappe.throw(f"Purchase Order '{purchase_order}' not found", frappe.DoesNotExistError)
    if po.docstatus != 1 or po.status not in RECEIVABLE_PO_STATUSES:
        frappe.throw(f"Purchase Order {purchase_order} is not open for receiving (status: {po.status})")
    if po.supplier != supplier:
        frappe.throw(f"Purchase Order {purchase_order} belongs to Supplier {po.supplier}, not {supplier}")
    if po.company != company:
        frappe.throw(f"Purchase Order {purchase_order} belongs to Company {po.company}, not {company}")

    pr_doc = make_receipt_from_po(purchase_order)
    po_rows = {row.purchase_order_item: row for row in pr_doc.get("items")}
    used_po_rows = set()
    pr_doc.set("items", [])

    for item in items:
        po_item = item.get("purchase_order_item")
        if po_item:
            row = po_rows.get(po_item)
            if not row:
                frappe.throw(f"Row {po_item} is not a pending item of Purchase Order {purchase_order}")
            if po_item in used_po_rows:
                frappe.throw(f"Purchase Order row {po_item} was sent more than once")
        else:
            # No row id sent: match the first unused PO row with the same item code
            row = next(
                (r for name, r in po_rows.items() if name not in used_po_rows and r.item_code == item.get("item_code")),
                None
            )

        qty = flt(item.get("qty"))

        if not row:
            # Extra item not on the PO
            row_data = {
                "item_code": item.get("item_code"),
                "qty": qty,
                "warehouse": accepted_warehouse,
                "rate": flt(item.get("rate"))
            }
            if item.get("uom"):
                row_data["uom"] = str(item.get("uom")).strip()
            if item.get("item_tax_template"):
                row_data["item_tax_template"] = str(item.get("item_tax_template")).strip()
            pr_doc.append("items", row_data)
            continue

        used_po_rows.add(row.purchase_order_item)

        uom = str(item.get("uom")).strip() if item.get("uom") else None
        if uom and uom != row.uom:
            row.uom = uom
            row.conversion_factor = get_conversion_factor(row.item_code, uom).get("conversion_factor") or 1

        row.qty = qty
        # The mapper copies the PO's received_qty; reset it so Received = Accepted + Rejected
        row.received_qty = qty + flt(row.rejected_qty)
        row.stock_qty = qty * flt(row.conversion_factor)
        row.warehouse = accepted_warehouse
        if item.get("item_tax_template"):
            row.item_tax_template = str(item.get("item_tax_template")).strip()
        if item.get("rate") not in (None, ""):
            row.rate = flt(item.get("rate"))

        pr_doc.append("items", row)

    pr_doc.set_warehouse = accepted_warehouse
    pr_doc.custom_purchase_order = purchase_order
    return pr_doc


@frappe.whitelist()
def get_supplier_purchase_invoices(supplier, company=None, search_term=None, limit_start=1, limit_page_length=20):
    """
    Fetch the submitted Purchase Invoices of a Supplier that still have items to be received
    (invoice made first on the web, with 'Update Stock' off). Used for the Purchase Invoice
    dropdown when creating a GRN.
    supplier: Exact name of the Supplier (Required)
    company: Optional company filter
    search_term: Optional search on invoice number
    """
    if not supplier:
        frappe.throw("Supplier is a required parameter")

    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    filters = {
        "supplier": str(supplier).strip(),
        "docstatus": 1,
        "is_return": 0,
        "update_stock": 0,
        "per_received": ["<", 100]
    }
    if company:
        filters["company"] = str(company).strip()
    if search_term:
        filters["name"] = ["like", f"%{str(search_term).strip()}%"]

    return frappe.get_all(
        "Purchase Invoice",
        filters=filters,
        fields=[
            "name", "supplier", "supplier_name", "posting_date", "bill_no", "bill_date",
            "company", "status", "grand_total", "per_received"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="posting_date DESC, name DESC"
    )


def _get_invoice_pending_rows(purchase_invoice):
    """Return receivable invoice rows, capped by any linked PO row's remaining quantity."""
    rows = frappe.get_all(
        "Purchase Invoice Item",
        filters={"parent": purchase_invoice, "parenttype": "Purchase Invoice"},
        fields=[
            "name", "item_code", "item_name", "uom", "stock_uom", "conversion_factor",
            "qty", "received_qty", "rate", "warehouse", "purchase_receipt", "pr_detail",
            "purchase_order", "po_detail", "is_fixed_asset"
        ],
        order_by="idx"
    )
    po_detail_names = [row.po_detail for row in rows if row.po_detail]
    po_pending_stock_qty = {}
    if po_detail_names:
        po_rows = frappe.get_all(
            "Purchase Order Item",
            filters={"name": ["in", po_detail_names]},
            fields=["name", "qty", "received_qty", "conversion_factor"]
        )
        po_pending_stock_qty = {
            row.name: max(
                (flt(row.qty) - flt(row.received_qty)) * flt(row.conversion_factor or 1),
                0
            )
            for row in po_rows
        }

    pending = []
    for row in rows:
        if row.pr_detail or row.is_fixed_asset or not row.item_code:
            continue
        if not frappe.db.get_value("Item", row.item_code, "is_stock_item"):
            continue
        pending_qty = flt(row.qty) - flt(row.received_qty)
        if pending_qty <= 0:
            continue
        if row.po_detail:
            conversion_factor = flt(row.conversion_factor or 1)
            pending_stock_qty = min(
                pending_qty * conversion_factor,
                po_pending_stock_qty.get(row.po_detail, 0)
            )
            pending_qty = pending_stock_qty / conversion_factor
            po_pending_stock_qty[row.po_detail] = max(
                po_pending_stock_qty.get(row.po_detail, 0) - pending_stock_qty,
                0
            )
            if pending_qty <= 0:
                continue
        row["pending_qty"] = pending_qty
        pending.append(row)
    return pending


@frappe.whitelist()
def get_purchase_invoice_pending_items(purchase_invoice):
    """
    Fetch a Purchase Invoice's items that are still pending to be received,
    so the mobile app can pre-fill the GRN items.
    purchase_invoice: Exact name of the Purchase Invoice (Required)

    Send each row's 'purchase_invoice_item' back in create_purchase_receipt's items
    so the GRN row is linked to the exact invoice row.
    """
    if not purchase_invoice:
        frappe.throw("Parameter 'purchase_invoice' is required")

    pi = frappe.db.get_value(
        "Purchase Invoice", purchase_invoice, ["supplier", "company", "docstatus"], as_dict=True
    )
    if not pi:
        frappe.throw(f"Purchase Invoice '{purchase_invoice}' not found", frappe.DoesNotExistError)

    items = [
        {
            "purchase_invoice_item": row.name,
            "item_code": row.item_code,
            "item_name": row.item_name,
            "uom": row.uom,
            "stock_uom": row.stock_uom,
            "conversion_factor": row.conversion_factor,
            "pending_qty": row.pending_qty,
            "rate": flt(row.rate),
            "warehouse": row.warehouse
        }
        for row in _get_invoice_pending_rows(purchase_invoice)
    ]

    return {
        "status": "success",
        "data": {
            "purchase_invoice": purchase_invoice,
            "supplier": pi.supplier,
            "company": pi.company,
            "items": items
        }
    }


def _build_receipt_from_purchase_invoice(purchase_invoice, supplier, company, items, accepted_warehouse):
    """
    Build a Purchase Receipt against a Purchase Invoice. Every row carries
    purchase_invoice / purchase_invoice_item (ERPNext's own link fields), so the invoice's
    received qty and 'Received %' update when the receipt is submitted.
    If the invoice row came from a Purchase Order, the PO link is carried over too.
    """
    pi = frappe.db.get_value(
        "Purchase Invoice", purchase_invoice,
        ["supplier", "company", "docstatus", "update_stock", "is_return"], as_dict=True
    )
    if not pi:
        frappe.throw(f"Purchase Invoice '{purchase_invoice}' not found", frappe.DoesNotExistError)
    if pi.docstatus != 1:
        frappe.throw(f"Purchase Invoice {purchase_invoice} must be submitted")
    if pi.update_stock or pi.is_return:
        frappe.throw(f"Purchase Invoice {purchase_invoice} cannot be received against (stock already updated or a return)")
    if pi.supplier != supplier:
        frappe.throw(f"Purchase Invoice {purchase_invoice} belongs to Supplier {pi.supplier}, not {supplier}")
    if pi.company != company:
        frappe.throw(f"Purchase Invoice {purchase_invoice} belongs to Company {pi.company}, not {company}")

    pi_rows = {row.name: row for row in _get_invoice_pending_rows(purchase_invoice)}
    used_rows = set()

    pr_doc = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "supplier": supplier,
        "company": company,
        "set_warehouse": accepted_warehouse
    })

    for item in items:
        pi_item = item.get("purchase_invoice_item")
        if pi_item:
            row = pi_rows.get(pi_item)
            if not row:
                frappe.throw(f"Row {pi_item} is not a pending item of Purchase Invoice {purchase_invoice}")
            if pi_item in used_rows:
                frappe.throw(f"Purchase Invoice row {pi_item} was sent more than once")
        else:
            # No row id sent: match the first unused invoice row with the same item code
            row = next(
                (r for name, r in pi_rows.items() if name not in used_rows and r.item_code == item.get("item_code")),
                None
            )

        qty = flt(item.get("qty"))
        uom = str(item.get("uom")).strip() if item.get("uom") else None

        if not row:
            # Extra item not on the invoice: normal, unlinked row
            row_data = {
                "item_code": item.get("item_code"),
                "qty": qty,
                "warehouse": accepted_warehouse,
                "rate": flt(item.get("rate"))
            }
            if uom:
                row_data["uom"] = uom
            if item.get("item_tax_template"):
                row_data["item_tax_template"] = str(item.get("item_tax_template")).strip()
            pr_doc.append("items", row_data)
            continue

        used_rows.add(row.name)

        row_data = {
            "item_code": row.item_code,
            "qty": qty,
            "received_qty": qty,
            "uom": uom or row.uom,
            "rate": flt(item.get("rate")) if item.get("rate") not in (None, "") else flt(row.rate),
            "warehouse": accepted_warehouse,
            "purchase_invoice": purchase_invoice,
            "purchase_invoice_item": row.name
        }
        conversion_factor = row.conversion_factor
        if uom and uom != row.uom:
            conversion_factor = get_conversion_factor(row.item_code, uom).get("conversion_factor") or 1
        requested_stock_qty = qty * flt(conversion_factor or 1)
        pending_stock_qty = flt(row.pending_qty) * flt(row.conversion_factor or 1)
        if requested_stock_qty > pending_stock_qty + 0.000000001:
            frappe.throw(
                f"Quantity for Purchase Invoice row {row.name} exceeds its remaining receivable quantity "
                "on the Purchase Invoice or linked Purchase Order"
            )
        row_data["conversion_factor"] = conversion_factor
        if row.purchase_order and row.po_detail:
            row_data["purchase_order"] = row.purchase_order
            row_data["purchase_order_item"] = row.po_detail
        if item.get("item_tax_template"):
            row_data["item_tax_template"] = str(item.get("item_tax_template")).strip()

        pr_doc.append("items", row_data)

    return pr_doc


def _apply_header_fields(pr_doc, branch=None, buying_price_list=None, tax_category=None, taxes_and_charges=None):
    """Set the optional header fields and load taxes from the chosen Purchase Taxes and Charges Template."""
    if branch:
        pr_doc.branch = str(branch).strip()
    if buying_price_list:
        pr_doc.buying_price_list = str(buying_price_list).strip()
    if tax_category:
        pr_doc.tax_category = str(tax_category).strip()
    if taxes_and_charges:
        from erpnext.controllers.accounts_controller import get_taxes_and_charges

        pr_doc.taxes_and_charges = str(taxes_and_charges).strip()
        # Replace any taxes copied from the PO with the template the user chose
        pr_doc.set("taxes", [])
        for tax in get_taxes_and_charges("Purchase Taxes and Charges Template", pr_doc.taxes_and_charges):
            pr_doc.append("taxes", tax)


@frappe.whitelist()
def create_purchase_receipt(supplier=None, company=None, items=None, accepted_warehouse=None, supplier_delivery_note=None, submit=0, purchase_order=None, branch=None, buying_price_list=None, tax_category=None, taxes_and_charges=None, purchase_invoice=None):
    """
    Create a new Purchase Receipt.
    supplier: Exact name of the Supplier (Required)
    company: Exact name of the Company (Optional, defaults to Global/User default)
    accepted_warehouse: The default warehouse for all items (Required)
    items: JSON string or list of dicts containing item_code, qty, rate, uom (Required).
           When purchase_order is sent, each item may also carry 'purchase_order_item'
           (from get_purchase_order_pending_items); rate is optional and defaults to the PO rate.
    supplier_delivery_note: Delivery note number provided by the supplier (Optional)
    submit: 1 to submit immediately, 0 to leave as Draft
    purchase_order: Purchase Order to receive against (Optional, must be 'To Receive and Bill')
    purchase_invoice: Purchase Invoice to receive against (Optional, web invoice with Update Stock off).
           Send either purchase_order or purchase_invoice, not both. Items then carry 'purchase_invoice_item'.
    branch: Branch (Optional)
    buying_price_list: Buying Price List (Optional)
    tax_category: Tax Category (Optional)
    taxes_and_charges: Purchase Taxes and Charges Template (Optional); its taxes are loaded into the receipt
    Each item may also carry 'item_tax_template' (Optional), along with uom and rate.
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

    for item in items:
        if not item.get("item_code") or not item.get("qty"):
            frappe.throw("Each item must contain at least an 'item_code' and 'qty'")

    supplier = str(supplier).strip()
    company = str(company).strip()
    accepted_warehouse = str(accepted_warehouse).strip()

    try:
        if purchase_order and purchase_invoice:
            frappe.throw("Send either purchase_order or purchase_invoice, not both")

        if purchase_order:
            # Linked GRN: built from the PO so the web shows the PO <-> PR connection
            pr_doc = _build_receipt_from_purchase_order(
                str(purchase_order).strip(), supplier, company, items, accepted_warehouse
            )
        elif purchase_invoice:
            # Linked GRN: rows carry the invoice link so the invoice's Received % updates
            pr_doc = _build_receipt_from_purchase_invoice(
                str(purchase_invoice).strip(), supplier, company, items, accepted_warehouse
            )
        else:
            pr_doc = frappe.get_doc({
                "doctype": "Purchase Receipt",
                "supplier": supplier,
                "company": company,
                "set_warehouse": accepted_warehouse # Sets the parent-level Accepted Warehouse
            })

            # Append items to the child table
            for item in items:
                row_data = {
                    "item_code": item.get("item_code"),
                    "qty": flt(item.get("qty")),
                    "warehouse": accepted_warehouse, # Assign the general warehouse to the item row
                    "rate": flt(item.get("rate")) if item.get("rate") else 0.0
                }

                if item.get("uom"):
                    row_data["uom"] = str(item.get("uom")).strip()
                if item.get("item_tax_template"):
                    row_data["item_tax_template"] = str(item.get("item_tax_template")).strip()

                pr_doc.append("items", row_data)

        # Add the optional supplier delivery note if provided
        if supplier_delivery_note:
            pr_doc.supplier_delivery_note = str(supplier_delivery_note).strip()

        # Insert the document (creates it as Draft)
        _apply_header_fields(pr_doc, branch, buying_price_list, tax_category, taxes_and_charges)

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
                "accepted_warehouse": pr_doc.set_warehouse,
                "purchase_order": pr_doc.get("custom_purchase_order"),
                "purchase_invoice": str(purchase_invoice).strip() if purchase_invoice else None,
                "branch": pr_doc.get("branch"),
                "buying_price_list": pr_doc.buying_price_list,
                "tax_category": pr_doc.tax_category,
                "taxes_and_charges": pr_doc.taxes_and_charges
            }
        }

    except Exception as e:
        # Log the error in Frappe's Error Log for easier debugging
        frappe.log_error(title="Purchase Receipt Creation API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to create Purchase Receipt: {str(e)}")