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
                fields=["name", "status", "transaction_date", "grand_total", "currency"]
            )

    return {
        "quotations": quotations,
        "sales_orders": sales_orders
    }
