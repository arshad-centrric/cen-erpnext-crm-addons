import frappe

def get_opportunity_for_sales_order(so_doc):
    """Traces from Sales Order -> Quotation -> Opportunity accurately."""
    for item in so_doc.items:
        quotation_name = getattr(item, "prevdoc_docname", None)
        
        # Ensure it's a Quotation by naming convention or check
        if quotation_name and "QTN" in quotation_name.upper():
            opp = frappe.db.get_value("Quotation", quotation_name, "opportunity")
            if opp:
                return opp
                
        # Fallback if mapped directly via quotation_item
        quotation_item_id = getattr(item, "quotation_item", None)
        if quotation_item_id and not quotation_name:
            quotation_name = frappe.db.get_value("Quotation Item", quotation_item_id, "parent")
            if quotation_name:
                opp = frappe.db.get_value("Quotation", quotation_name, "opportunity")
                if opp:
                    return opp
    return None

def on_sales_order_update(doc, method):
    """Hook 1: Syncs SO payment & picking status to Opportunity."""
    opp_name = get_opportunity_for_sales_order(doc)
    if not opp_name:
        return
        
    opp = frappe.get_doc("Opportunity", opp_name)
    needs_save = False
    
    # 1. Sync Payment Status
    if doc.custom_payment_status:
        opp_payment_status = "Pending" if doc.custom_payment_status == "Unpaid" else doc.custom_payment_status
        if opp.custom_payment_status != opp_payment_status:
            opp.custom_payment_status = opp_payment_status
            needs_save = True

    # 2. Sync Picking Status -> Packed
    if doc.get("custom_picking_status") == "Packed" and opp.status not in ("Delivered", "To be paid", "Closed"):
        opp.status = "Packed"
        needs_save = True
        
    # 3. Edge Case: Paid + To be paid/Delivered -> Closed
    if doc.custom_payment_status == "Paid" and opp.status in ("To be paid", "Delivered"):
        opp.status = "Closed"
        needs_save = True
        
    if needs_save:
        # Save explicitly via DB to avoid standard Frappe before_save 'Converted' override
        opp.db_set("custom_payment_status", opp.custom_payment_status, update_modified=True)
        opp.db_set("status", opp.status, update_modified=True)

def on_delivery_note_submit(doc, method):
    """Hook 2: Updates Opportunity status on DN Submit."""
    # 1. Find the parent Sales Order
    so_name = None
    for item in doc.items:
        if item.against_sales_order:
            so_name = item.against_sales_order
            break
            
    if not so_name:
        return
        
    so_doc = frappe.get_doc("Sales Order", so_name)
    opp_name = get_opportunity_for_sales_order(so_doc)
    
    if not opp_name:
        return
        
    opp = frappe.get_doc("Opportunity", opp_name)
    
    # Check SO payment status according to client business rules
    if so_doc.custom_payment_status == "Paid":
        opp.status = "Closed"
    else:
        opp.status = "Delivered"
        
    opp.db_set("status", opp.status, update_modified=True)

def on_payment_entry_submit(doc, method):
    """Hook 3: Ensures Opportunity syncs instantly when a Payment is made against the SO."""
    for ref in getattr(doc, "references", []):
        if ref.reference_doctype == "Sales Order":
            so_doc = frappe.get_doc("Sales Order", ref.reference_name)
            # Re-evaluate the logic by triggering the SO hook directly
            on_sales_order_update(so_doc, None)
