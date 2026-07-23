import frappe
import json
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import flt

@frappe.whitelist()
def submit_multi_mode_payment(sales_order, payments, write_off_amount=0.0):
    if isinstance(payments, str):
        payments = json.loads(payments)
        
    write_off_amount = flt(write_off_amount)
    pe_ids = []
    
    for i, payment in enumerate(payments):
        pe = get_payment_entry("Sales Order", sales_order)
        
        # Override amounts
        amount = flt(payment.get("amount"))
        pe.paid_amount = amount
        pe.received_amount = amount
        pe.base_paid_amount = amount
        pe.base_received_amount = amount
        
        if payment.get("mode_of_payment"):
            pe.mode_of_payment = payment.get("mode_of_payment")
        
        # Write-off logic (first payment only)
        if write_off_amount > 0 and i == 0:
            write_off_account = frappe.db.get_value("Company", pe.company, "write_off_account")
            if not write_off_account:
                frappe.throw("Write-off account not found for company")
            
            cost_center = pe.cost_center
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
        
    return pe_ids

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
