import frappe

@frappe.whitelist()
def get_opportunity_for_doc(doctype, docname):
    if doctype == "Quotation":
        return frappe.db.get_value("Quotation", docname, "opportunity")
        
    elif doctype == "Sales Order":
        quotation_items = frappe.get_all(
            "Sales Order Item",
            filters={"parent": docname, "prevdoc_docname": ("like", "SAL-QTN%"), "prevdoc_docname": ("is", "set")},
            fields=["prevdoc_docname"]
        )
        if quotation_items:
            quotation_names = [q["prevdoc_docname"] for q in quotation_items]
            return frappe.db.get_value(
                "Quotation",
                {"name": ("in", quotation_names), "opportunity": ("is", "set")},
                "opportunity"
            )
            
    elif doctype == "Payment Entry":
        refs = frappe.get_all(
            "Payment Entry Reference", 
            filters={"parent": docname, "reference_doctype": "Sales Order"}, 
            fields=["reference_name"]
        )
        if refs:
            # Try to trace back from the first Sales Order reference
            for ref in refs:
                opp = get_opportunity_for_doc("Sales Order", ref.reference_name)
                if opp:
                    return opp
                    
    return None

@frappe.whitelist()
def get_wa_link_for_doc(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    mobile = None
    
    if hasattr(doc, 'contact_mobile') and doc.contact_mobile:
        mobile = doc.contact_mobile
    elif hasattr(doc, 'mobile_no') and doc.mobile_no:
        mobile = doc.mobile_no
        
    if not mobile and doctype == "Payment Entry" and doc.get("party_type") in ("Customer", "Lead") and doc.get("party"):
        mobile = frappe.db.get_value(doc.party_type, doc.party, "mobile_no")
        
    if mobile:
        phone = "".join(filter(str.isdigit, str(mobile)))
        if phone:
            return f"https://wa.me/{phone}"
            
    return None

@frappe.whitelist()
def get_linked_documents(opportunity_name):
    # 1. Fetch Quotations linked to this Opportunity
    quotations = frappe.get_all(
        "Quotation",
        filters={"opportunity": opportunity_name},
        fields=["name", "status", "transaction_date", "grand_total", "currency", "custom_revision_reason"]
    )

    sales_orders = []
    sales_invoices = []

    if quotations:
        quotation_names = [q["name"] for q in quotations]
        
        # 2. Fetch Sales Orders linked to these Quotations via items table
        # Since standard Frappe links SO to Quotation in the Items table (prevdoc_docname)
        # Or sometimes directly mapped. Using get_all on SO Items table to find parent.
        
        so_items = frappe.get_all(
            "Sales Order Item",
            filters={"prevdoc_docname": ("in", quotation_names)},
            fields=["parent", "prevdoc_docname"]
        )

        so_names = list(set([item["parent"] for item in so_items]))

        if so_names:
            sales_orders = frappe.get_all(
                "Sales Order",
                filters={"name": ("in", so_names)},
                fields=["name", "status", "transaction_date", "grand_total", "currency", 
                        "custom_picking_status", "custom_payment_status", "delivery_status", "custom_packing_image", "advance_paid"]
            )
            
            # For each Sales Order, calculate due amount and check for attached files
            for so in sales_orders:
                from frappe.utils import flt
                # Calculate Due Amount factoring in Sales Invoices
                linked_invoices = frappe.db.sql("""
                    SELECT DISTINCT si.name, si.outstanding_amount
                    FROM `tabSales Invoice` si
                    JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
                    WHERE sii.sales_order = %s AND si.docstatus = 1
                """, (so["name"],), as_dict=True)

                if linked_invoices:
                    so["due_amount"] = sum(flt(inv.outstanding_amount) for inv in linked_invoices)
                else:
                    so["due_amount"] = flt(so.get("grand_total")) - flt(so.get("advance_paid"))

                so["payment_entries"] = []
                
                # Find Payment Entries linked to this SO
                pe_refs = frappe.get_all(
                    "Payment Entry Reference",
                    filters={"reference_doctype": "Sales Order", "reference_name": so["name"]},
                    fields=["parent"]
                )
                pe_names = list(set([ref["parent"] for ref in pe_refs]))
                
                if pe_names:
                    # Find Payment Entries Details
                    pes = frappe.get_all(
                        "Payment Entry",
                        filters={"name": ("in", pe_names), "docstatus": 1},
                        fields=["name", "mode_of_payment", "paid_amount"]
                    )
                        
                    # Find Files attached to those Payment Entries
                    files = frappe.get_all(
                        "File",
                        filters={"attached_to_doctype": "Payment Entry", "attached_to_name": ("in", pe_names)},
                        fields=["file_url", "file_name", "attached_to_name"]
                    )
                    
                    so["payment_entries"] = pes
                    for pe in so["payment_entries"]:
                        pe["files"] = [f for f in files if f.attached_to_name == pe["name"]]
                        
        if so_names:
            si_names_query = frappe.db.sql("""
                SELECT DISTINCT si.name
                FROM `tabSales Invoice` si
                JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
                WHERE sii.sales_order IN %s AND si.docstatus = 1
            """, (tuple(so_names),), pluck=True)
            
            if si_names_query:
                sales_invoices = frappe.get_all(
                    "Sales Invoice",
                    filters={"name": ("in", si_names_query)},
                    fields=["name", "status", "posting_date", "grand_total", "currency", "outstanding_amount"]
                )
                
                for si in sales_invoices:
                    si["transaction_date"] = si.get("posting_date") # Map for frontend uniformity
                    si["payment_entries"] = []
                    
                    # Find Payment Entries linked to this SI
                    pe_refs = frappe.get_all(
                        "Payment Entry Reference",
                        filters={"reference_doctype": "Sales Invoice", "reference_name": si["name"]},
                        fields=["parent"]
                    )
                    pe_names = list(set([ref["parent"] for ref in pe_refs]))
                    
                    if pe_names:
                        # Find Payment Entries Details
                        pes = frappe.get_all(
                            "Payment Entry",
                            filters={"name": ("in", pe_names), "docstatus": 1},
                            fields=["name", "mode_of_payment", "paid_amount"]
                        )
                            
                        # Find Files attached to those Payment Entries
                        files = frappe.get_all(
                            "File",
                            filters={"attached_to_doctype": "Payment Entry", "attached_to_name": ("in", pe_names)},
                            fields=["file_url", "file_name", "attached_to_name"]
                        )
                        
                        si["payment_entries"] = pes
                        for pe in si["payment_entries"]:
                            pe["files"] = [f for f in files if f.attached_to_name == pe["name"]]
                        
    return {
        "quotations": quotations,
        "sales_orders": sales_orders,
        "sales_invoices": sales_invoices
    }
