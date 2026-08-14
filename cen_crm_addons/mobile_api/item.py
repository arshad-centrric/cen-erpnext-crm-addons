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
    if frappe.db.has_column("Item", "custom_is_customized_bundle"):
        filters["custom_is_customized_bundle"] = ["!=", 1]
        
    or_filters = {}
    
    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        or_filters = {
            "item_code": ["like", search_string],
            "item_name": ["like", search_string]
        }
        
        matching_barcodes = frappe.get_all(
            "Item Barcode",
            filters={"barcode": ["like", search_string]},
            pluck="parent"
        )
        if matching_barcodes:
            or_filters["name"] = ["in", matching_barcodes]

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
        fields=["item_code", "price_list_rate", "selling", "buying", "price_list", "uom"]
    )
    
    prices_map = {}
    for ip in item_prices:
        if ip.item_code not in prices_map:
            prices_map[ip.item_code] = {"selling": {}, "buying": {}}
            
        # Prepare lowercase comparison variables safely
        target_sell = str(selling_price_list).strip().lower() if selling_price_list else None
        target_buy = str(buying_price_list).strip().lower() if buying_price_list else None
        
        # Match selling price list (case-insensitive)
        if target_sell and str(ip.price_list).lower() == target_sell:
            prices_map[ip.item_code]["selling"][ip.uom] = ip.price_list_rate
            
        # Match buying price list (case-insensitive)
        if target_buy and str(ip.price_list).lower() == target_buy:
            prices_map[ip.item_code]["buying"][ip.uom] = ip.price_list_rate

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
        default_uom = item.default_uom
        
        # Strictly require an explicit Item Price for the Default UOM. Otherwise, default to 0.0.
        explicit_selling = 0.0
        explicit_buying = 0.0
        
        if code in prices_map:
            if prices_map[code]["selling"].get(default_uom) is not None:
                explicit_selling = prices_map[code]["selling"][default_uom]

            if prices_map[code]["buying"].get(default_uom) is not None:
                explicit_buying = prices_map[code]["buying"][default_uom]
                
        item.selling_rate = flt(explicit_selling)
        item.buying_rate = flt(explicit_buying)
        
        # Collect all unique UOMs linked to this item from the UOM Conversion Details table ONLY
        all_uoms = {default_uom}
        
        for u in uom_map.get(code, []):
            all_uoms.add(u["uom"])
                
        item.uom_details = []
        
        for uom_name in sorted(all_uoms):
            # Find conversion factor (defaults to 1.0 if not in UOM table)
            conv_factor = 1.0
            if uom_name != default_uom:
                for u in uom_map.get(code, []):
                    if u["uom"] == uom_name:
                        conv_factor = u["conversion_factor"]
                        break
                        
            # Determine specific UOM prices
            u_sell = prices_map.get(code, {}).get("selling", {}).get(uom_name)
            if u_sell is None:
                u_sell = item.selling_rate * flt(conv_factor)
                
            u_buy = prices_map.get(code, {}).get("buying", {}).get(uom_name)
            if u_buy is None:
                u_buy = item.buying_rate * flt(conv_factor)
                
            item.uom_details.append({
                "uom": uom_name,
                "conversion_factor": flt(conv_factor),
                "selling_rate": flt(u_sell),
                "buying_rate": flt(u_buy)
            })
        
        # Attach Barcodes (from child table)
        item.barcodes = barcode_map.get(code, [])
        
        # Clean up temporary DB fields
        item.pop("name", None)

    return items


@frappe.whitelist()
def get_item_groups(search_term="", limit_start=1, limit_page_length=20):
    limit = int(limit_page_length)
    offset = (int(limit_start) - 1) * limit
    
    filters = {}
    if search_term:
        filters = {"name": ["like", f"%{search_term}%"]}
        
    return frappe.db.get_list(
        "Item Group",
        filters=filters,
        fields=["name"],
        limit_start=offset,
        limit_page_length=limit
    )

@frappe.whitelist()
def get_uoms(search_term="", limit_start=1, limit_page_length=20):
    limit = int(limit_page_length)
    offset = (int(limit_start) - 1) * limit
    
    filters = {}
    if search_term:
        filters = {"name": ["like", f"%{search_term}%"]}
        
    return frappe.db.get_list(
        "UOM",
        filters=filters,
        fields=["name"],
        limit_start=offset,
        limit_page_length=limit
    )

@frappe.whitelist()
def get_hsn_codes(search_term="", limit_start=1, limit_page_length=20):
    limit = int(limit_page_length)
    offset = (int(limit_start) - 1) * limit
    
    or_filters = {}
    if search_term:
        or_filters = {
            "name": ["like", f"%{search_term}%"],
            "description": ["like", f"%{search_term}%"]
        }
        
    return frappe.db.get_list(
        "GST HSN Code",
        or_filters=or_filters,
        fields=["name", "description"],
        limit_start=offset,
        limit_page_length=limit
    )

@frappe.whitelist()
def create_item(**kwargs):
    try:
        # Handle both direct JSON body and stringified 'item_data' form field
        if "item_data" in kwargs and isinstance(kwargs["item_data"], str):
            data = frappe.parse_json(kwargs["item_data"])
        else:
            data = frappe._dict(kwargs)
        
        item_doc = frappe.new_doc("Item")
        item_doc.item_name = data.get("item_name")
        item_doc.item_group = data.get("item_group")
        item_doc.stock_uom = data.get("default_uom")
        
        warning_msg = ""
        
        if data.get("hsn_code"):
            meta = frappe.get_meta("Item")
            hsn_val = data.get("hsn_code")
            if meta.has_field("gst_hsn_code"):
                if frappe.db.exists("GST HSN Code", hsn_val):
                    item_doc.gst_hsn_code = hsn_val
                else:
                    warning_msg = f" (Note: HSN Code '{hsn_val}' was ignored as it does not exist in GST HSN Code list)"
            elif meta.has_field("custom_hsnsac"):
                if frappe.db.exists("HSN SAC", hsn_val):
                    item_doc.custom_hsnsac = hsn_val
                else:
                    warning_msg = f" (Note: HSN Code '{hsn_val}' was ignored as it does not exist in HSN SAC list)"
            elif meta.has_field("customs_tariff_number"):
                if frappe.db.exists("Customs Tariff Number", hsn_val):
                    item_doc.customs_tariff_number = hsn_val
                else:
                    warning_msg = f" (Note: Customs Tariff Number '{hsn_val}' was ignored as it does not exist)"
            else:
                warning_msg = " (Note: HSN Code not saved because no matching HSN field was found on the system)"
            
        barcodes = data.get("barcodes", [])
        if isinstance(barcodes, str):
            barcodes = frappe.parse_json(barcodes)
            
        for b in barcodes:
            item_doc.append("barcodes", {"barcode": b.get("barcode"), "uom": b.get("uom")})
            
        uom_conversions = data.get("uom_conversions", [])
        if isinstance(uom_conversions, str):
            uom_conversions = frappe.parse_json(uom_conversions)
            
        for u in uom_conversions:
            item_doc.append("uoms", {"uom": u.get("uom"), "conversion_factor": u.get("conversion_factor")})
            
        item_doc.insert(ignore_permissions=True)
        
        price_list = data.get("selling_price_list")
        rate = data.get("selling_rate")
        
        if price_list and rate:
            price_doc = frappe.new_doc("Item Price")
            price_doc.item_code = item_doc.name
            price_doc.price_list = price_list
            price_doc.price_list_rate = rate
            price_doc.insert(ignore_permissions=True)
            
        return {
            "status": "success", 
            "item_code": item_doc.name, 
            "message": f"Item created successfully{warning_msg}"
        }
    except Exception as e:
        frappe.log_error(title="Mobile Item Creation Failed", message=frappe.get_traceback())
        frappe.local.response['http_status_code'] = 400
        return {"status": "error", "message": str(e)}