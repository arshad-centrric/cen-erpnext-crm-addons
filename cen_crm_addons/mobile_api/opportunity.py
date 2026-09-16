import frappe


@frappe.whitelist()
def admin_opportunity_list(status=None, search_term=None, limit_start=1, limit_page_length=20, company=None, branch=None):
    """
    Fetch a paginated list of Opportunities.
    If 'status' is not provided, defaults to showing both 'To be quoted' and 'Revise the Quote'.
    """
    resolved_branch = branch or frappe.defaults.get_user_default("branch")
    
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    if status:
        filters = {"status": str(status).strip()}
    else:
        filters = {"status": ["in", ["To be quoted", "Revise the Quote"]]}
        
    if company:
        filters["company"] = str(company).strip()

    if resolved_branch and str(resolved_branch).strip() and resolved_branch != "All Branches":
        filters["custom_cen_branch"] = str(resolved_branch).strip()

    or_filters = {}
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "name": ["like", search_string],
            "party_name": ["like", search_string],
            "customer_name": ["like", search_string]
        }

    opportunities = frappe.get_all(
        "Opportunity",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "opportunity_from",
            "party_name",
            "customer_name",
            "transaction_date",
            "status",
            "opportunity_amount",
            "custom_assigned_to",
            "custom_assigned_full_name",
            "custom_box_id",
            "custom_cen_branch as branch"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="modified DESC"
    )

    return opportunities


@frappe.whitelist()
def get_opportunity_details(opportunity_id):
    """
    Fetch all details of a specific Opportunity including its items and custom fields.
    """
    if not opportunity_id:
        frappe.throw("Opportunity ID is required")

    try:
        doc = frappe.get_doc("Opportunity", opportunity_id)
        data = doc.as_dict()
        
        # Fetch linked quotations (excluding cancelled ones)
        quotations = frappe.get_all(
            "Quotation",
            filters={"opportunity": opportunity_id, "docstatus": ["<", 2]},
            fields=["name", "status", "docstatus", "grand_total", "transaction_date"]
        )
        data["linked_quotations"] = quotations

        return {
            "status": "success",
            "data": data
        }
    except frappe.DoesNotExistError:
        frappe.throw(f"Opportunity {opportunity_id} not found")
    except Exception as e:
        frappe.log_error(title="Fetch Opportunity Details API Error", message=frappe.get_traceback())
        frappe.throw(f"Failed to fetch details: {e!s}")
