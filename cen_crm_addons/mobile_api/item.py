import frappe
from frappe.utils import flt


@frappe.whitelist()
def item_list(search_term=None, limit_start=1, limit_page_length=20, selling_price_list=None, buying_price_list=None):
    """
    Fetch a detailed, paginated list of active Items.
    Returns: item_code, item_name, default_uom, hsn_code, selling_rate, buying_rate, multiple UOMs, barcodes
    """
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = (page - 1) * page_length
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    filters = {"disabled": 0}
    or_filters = {}
    
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "item_code": ["like", search_string],
            "item_name": ["like", search_string]
        }

    # 1. Dynamically find the correct HSN Field based on installed apps
    meta = frappe.get_meta("Item")
    if meta.has_field("gst_hsn_code"):
        hsn_field = "gst_hsn_code"
    elif meta.has_field("custom_hsnsac"):
        hsn_field = "custom_hsnsac"
    else:
        hsn_field = "customs_tariff_number"

    # 2. Fetch core items
    items = frappe.get_all(
        "Item",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "item_code",
            "item_name",
            "item_group",
            "stock_uom as default_uom",
            f"{hsn_field} as hsn_code",
            "standard_rate as selling_rate",
            "valuation_rate as buying_rate"
        ],
        limit_start=limit_start_idx,
        limit_page_length=page_length,
        order_by="item_name ASC"
    )

    if not items:
        return []

    item_codes = [d.item_code for d in items]

    # 2. Bulk fetch Item Prices to override base rates
    item_prices = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", item_codes]},
        fields=["item_code", "price_list_rate", "selling", "buying", "price_list"]
    )
    
    prices_map = {}
    for ip in item_prices:
        if ip.item_code not in prices_map:
            prices_map[ip.item_code] = {"selling": None, "buying": None}
            
        # Match selling price list (or fallback to default selling)
        if selling_price_list:
            if ip.price_list == selling_price_list:
                prices_map[ip.item_code]["selling"] = ip.price_list_rate
        elif ip.selling == 1 and prices_map[ip.item_code]["selling"] is None:
            prices_map[ip.item_code]["selling"] = ip.price_list_rate
            
        # Match buying price list (or fallback to default buying)
        if buying_price_list:
            if ip.price_list == buying_price_list:
                prices_map[ip.item_code]["buying"] = ip.price_list_rate
        elif ip.buying == 1 and prices_map[ip.item_code]["buying"] is None:
            prices_map[ip.item_code]["buying"] = ip.price_list_rate

    # 3. Bulk fetch Multiple UOMs
    uoms = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": ["in", item_codes]},
        fields=["parent as item_code", "uom", "conversion_factor"]
    )
    
    uom_map = {}
    for u in uoms:
        uom_map.setdefault(u.item_code, []).append({
            "uom": u.uom,
            "conversion_factor": u.conversion_factor
        })

    # 4. Bulk fetch Barcodes
    barcodes = frappe.get_all(
        "Item Barcode",
        filters={"parent": ["in", item_codes]},
        fields=["parent as item_code", "barcode", "uom"]
    )
    
    barcode_map = {}
    for b in barcodes:
        barcode_map.setdefault(b.item_code, []).append({
            "barcode": b.barcode,
            "uom": b.uom
        })

    # 5. Assemble final response
    for item in items:
        code = item.item_code
        
        # Override selling/buying rate if an Item Price exists
        if code in prices_map:
            if prices_map[code]["selling"] is not None:
                item.selling_rate = prices_map[code]["selling"]
            if prices_map[code]["buying"] is not None:
                item.buying_rate = prices_map[code]["buying"]
                
        # Ensure rates are at least 0.0
        item.selling_rate = flt(item.selling_rate)
        item.buying_rate = flt(item.buying_rate)
        
        # Attach UOMs
        item.uom_details = uom_map.get(code, [])
        
        # Attach Barcodes (from child table)
        item.barcodes = barcode_map.get(code, [])
        
        # Clean up temporary DB fields
        item.pop("name", None)

    return items