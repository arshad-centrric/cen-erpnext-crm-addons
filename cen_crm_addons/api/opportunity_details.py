import frappe

@frappe.whitelist()
def get_linked_documents(opportunity_name):
    # 1. Fetch Quotations linked to this Opportunity
    quotations = frappe.get_all(
        "Quotation",
        filters={"opportunity": opportunity_name},
        fields=["name", "status", "transaction_date", "grand_total", "currency"]
    )

    sales_orders = []

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
                        "custom_picking_status", "custom_payment_status", "delivery_status"]
            )
            
            # For each Sales Order, check for attached files in their Payment Entries
            for so in sales_orders:
                so["payment_entries"] = []
                payment_status = so.get("custom_payment_status") or ""
                
                if "unpaid" not in payment_status.strip().lower() and "pending" not in payment_status.strip().lower():
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
                            filters={"name": ("in", pe_names), "docstatus": ("<", 2)},
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
                        
    return {
        "quotations": quotations,
        "sales_orders": sales_orders
    }
