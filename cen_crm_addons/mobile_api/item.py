import frappe

@frappe.whitelist()
def get_items(search_term=None, limit_start=1, limit_page_length=20):
    """
    Fetch a paginated list of active Items.
    search_term: String to search by item_code or item_name
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

    # Base filters (only active items)
    filters = {
        "disabled": 0
    }

    # Optional search filters (OR conditions)
    or_filters = {}
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "item_code": ["like", search_string],
            "item_name": ["like", search_string]
        }

    items = frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "item_code",
            "item_name",
            "standard_rate as rate"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="item_name ASC"
    )

    return items