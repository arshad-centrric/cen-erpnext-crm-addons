import frappe
import json
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import flt
from cen_crm_addons.api.payment_logic import sync_payment_status

@frappe.whitelist()
def submit_multi_mode_payment(sales_order, payments, write_off_amount=0.0):
    if isinstance(payments, str):
        payments = json.loads(payments)
        
    write_off_amount = flt(write_off_amount)
    pe_ids = []
    
    # Dynamic routing: check for active Sales Invoice
    active_si = frappe.db.sql("""
        SELECT si.name 
        FROM `tabSales Invoice` si 
        JOIN `tabSales Invoice Item` sii ON sii.parent = si.name 
        WHERE sii.sales_order = %s AND si.docstatus = 1 
        LIMIT 1
    """, (sales_order,))
    
    if active_si:
        target_doctype = "Sales Invoice"
        target_docname = active_si[0][0]
    else:
        target_doctype = "Sales Order"
        target_docname = sales_order
    
    for i, payment in enumerate(payments):
        pe = get_payment_entry(target_doctype, target_docname)
        
        # Override amounts
        amount = flt(payment.get("amount"))
        pe.paid_amount = amount
        pe.received_amount = amount
        pe.base_paid_amount = amount
        pe.base_received_amount = amount
        
        if payment.get("mode_of_payment"):
            pe.mode_of_payment = payment.get("mode_of_payment")
            
        if pe.references:
            pe.references[0].reference_doctype = target_doctype
            pe.references[0].reference_name = target_docname
        else:
            pe.append("references", {
                "reference_doctype": target_doctype,
                "reference_name": target_docname,
                "allocated_amount": amount
            })
        
        # Write-off logic (first payment only)
        if write_off_amount > 0 and i == 0:
            write_off_account = frappe.db.get_value("Company", pe.company, "write_off_account")
            if not write_off_account:
                frappe.throw("Write-off account not found for company")
            
            cost_center = pe.cost_center
            if not cost_center and target_doctype == "Sales Invoice":
                cost_center = frappe.db.get_value("Sales Invoice Item", {"parent": target_docname}, "cost_center")
            if not cost_center:
                cost_center = frappe.db.get_value("Sales Order Item", {"parent": sales_order}, "cost_center")
            if not cost_center:
                cost_center = frappe.db.get_value("Company", pe.company, "cost_center")
            
            pe.append("deductions", {
                "account": write_off_account,
                "cost_center": cost_center,
                "amount": write_off_amount
            })
            pe.references[0].allocated_amount = amount + write_off_amount
        else:
            pe.references[0].allocated_amount = amount
            
        # Bank mandatory fields
        mop_type = frappe.db.get_value("Mode of Payment", pe.mode_of_payment, "type")
        if mop_type == "Bank":
            pe.reference_no = payment.get("reference_no") or frappe.generate_hash()[:8]
            pe.reference_date = payment.get("reference_date") or frappe.utils.today()
            
        # Attachment & Submission
        if payment.get("attachment"):
            pe.custom_payment_screenshot = payment.get("attachment")
            
        pe.save(ignore_permissions=True)
        pe.submit()
        pe_ids.append(pe.name)
        
    sync_payment_status(sales_order)
        
    return {
        "status": "success",
        "payment_entries": pe_ids,
        "target_document": {
            "doctype": target_doctype,
            "name": target_docname
        }
    }

@frappe.whitelist()
def get_mode_of_payment_list():
    user = frappe.session.user
    
    modes = frappe.get_list("Mode of Payment", fields=["name", "type"], ignore_permissions=False)
    
    response = []
    for mode in modes:
        response.append({
            "mode_of_payment": mode.name,
            "mandatory_fields": 1 if mode.type in ["Bank", "Cheque"] else 0
        })
        
    return response

@frappe.whitelist()
def get_payment_attachments(sales_order):
    """
    Fetch all Payment Entries and their file attachments linked to a specific Sales Order.
    Includes reference details (cheque numbers) and write-off amounts.
    """
    if not sales_order:
        frappe.throw("Sales Order parameter is required.")
        
    # Check for active Sales Invoices linked to this Sales Order
    linked_invoices = frappe.db.sql("""
        SELECT DISTINCT parent 
        FROM `tabSales Invoice Item`
        WHERE sales_order = %s AND docstatus = 1
    """, (sales_order,), pluck=True)
    
    # Find Payment Entries based on Invoices or Sales Order
    if linked_invoices:
        payment_references = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "reference_doctype": "Sales Invoice",
                "reference_name": ["in", linked_invoices],
                "docstatus": 1
            },
            fields=["parent", "allocated_amount", "reference_doctype", "reference_name"]
        )
    else:
        payment_references = frappe.get_all(
            "Payment Entry Reference",
            filters={
                "reference_doctype": "Sales Order",
                "reference_name": sales_order,
                "docstatus": 1
            },
            fields=["parent", "allocated_amount", "reference_doctype", "reference_name"]
        )
    
    pe_ids = [ref.parent for ref in payment_references]
    
    if not pe_ids:
        return []
        
    # Fetch Payment Entry core details including reference info
    payment_entries = frappe.get_all(
        "Payment Entry",
        filters={"name": ["in", pe_ids]},
        fields=["name", "posting_date", "mode_of_payment", "paid_amount", "reference_no", "reference_date"]
    )
    
    # Fetch deductions to calculate write-off amount
    deductions = frappe.get_all(
        "Payment Entry Deduction",
        filters={"parent": ["in", pe_ids]},
        fields=["parent", "amount"]
    )
        
    # Query standard sidebar File attachments
    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Payment Entry",
            "attached_to_name": ["in", pe_ids]
        },
        fields=["file_url", "file_name", "attached_to_name"]
    )
    
    # Map attachments and amounts to Payment Entries
    response = []
    
    for pe in payment_entries:
        pe_attachments = []
        
        # Standard sidebar files
        for f in files:
            if f.attached_to_name == pe.name:
                pe_attachments.append({
                    "file_url": f.file_url,
                    "file_name": f.file_name
                })
                
        # Calculate write off amount from deductions
        write_off_amount = sum(flt(d.amount) for d in deductions if d.parent == pe.name)
                
        # Find allocated amount and references
        allocated = 0
        ref_doctype = None
        ref_name = None
        for ref in payment_references:
            if ref.parent == pe.name:
                allocated = ref.allocated_amount
                ref_doctype = ref.reference_doctype
                ref_name = ref.reference_name
                break
                
        response.append({
            "payment_entry": pe.name,
            "posting_date": pe.posting_date,
            "mode_of_payment": pe.mode_of_payment,
            "paid_amount": pe.paid_amount,
            "allocated_amount": allocated,
            "write_off_amount": write_off_amount,
            "reference_no": pe.reference_no,
            "reference_date": pe.reference_date,
            "reference_doctype": ref_doctype,
            "reference_name": ref_name,
            "attachments": pe_attachments
        })
            
    return response
