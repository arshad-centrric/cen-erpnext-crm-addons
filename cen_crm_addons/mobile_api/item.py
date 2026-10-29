import frappe
from frappe.utils import flt


@frappe.whitelist()
def item_list(search_term=None, limit_start=1, limit_page_length=20, selling_price_list=None, buying_price_list=None, exact_item_code=None, company=None):
    """
    Fetch a detailed, paginated list of active Items.
    Returns: item_code, item_name, default_uom, hsn_code, selling_rate, buying_rate, multiple UOMs, barcodes, item_tax_templates
    """
    try:
        page = int(limit_start)
        page_length = int(limit_page_length)
        limit_start_idx = max(0, (page - 1) * page_length)
    except (ValueError, TypeError):
        limit_start_idx = 0
        page_length = 20

    # 1. Dynamically find the correct HSN Field based on installed apps
    meta = frappe.get_meta("Item")
    if meta.has_field("gst_hsn_code"):
        hsn_field = "gst_hsn_code"
    elif meta.has_field("custom_hsnsac"):
        hsn_field = "custom_hsnsac"
    else:
        hsn_field = "customs_tariff_number"

    # Base query conditions
    conditions = ["item.disabled = 0"]
    values = {
        "limit_start": limit_start_idx,
        "limit_page_length": page_length,
    }

    if frappe.db.has_column("Item", "custom_is_customized_bundle"):
        conditions.append("COALESCE(item.custom_is_customized_bundle, 0) != 1")

    if exact_item_code:
        conditions.append("item.item_code = %(exact_item_code)s")
        values["exact_item_code"] = exact_item_code

    if search_term:
        search_string = f"%{str(search_term).strip()}%"
        values["search_string"] = search_string
        conditions.append("""(
            item.item_code LIKE %(search_string)s 
            OR item.item_name LIKE %(search_string)s 
            OR EXISTS (
                SELECT 1 FROM `tabItem Barcode` ib 
                WHERE ib.parent = item.name AND ib.barcode LIKE %(search_string)s
            )
        )""")

    # Filter at query level: only items having price_list_rate > 0 in the requested price list for a valid UOM
    target_sell = str(selling_price_list).strip() if selling_price_list and str(selling_price_list).strip() else None
    target_buy = str(buying_price_list).strip() if buying_price_list and str(buying_price_list).strip() else None

    if not exact_item_code and (target_sell or target_buy):
        uom_valid_sql = """(
            ip.uom = item.stock_uom 
            OR ip.uom IS NULL 
            OR ip.uom = '' 
            OR EXISTS (
                SELECT 1 FROM `tabUOM Conversion Detail` ucd 
                WHERE ucd.parent = item.name AND ucd.uom = ip.uom
            )
        )"""

        if target_sell and target_buy:
            conditions.append(f"""(
                EXISTS (
                    SELECT 1 FROM `tabItem Price` ip 
                    WHERE ip.item_code = item.name 
                      AND ip.price_list = %(selling_price_list)s 
                      AND ip.price_list_rate > 0
                      AND {uom_valid_sql}
                )
                OR
                EXISTS (
                    SELECT 1 FROM `tabItem Price` ip 
                    WHERE ip.item_code = item.name 
                      AND ip.price_list = %(buying_price_list)s 
                      AND ip.price_list_rate > 0
                      AND {uom_valid_sql}
                )
            )""")
            values["selling_price_list"] = target_sell
            values["buying_price_list"] = target_buy
        elif target_sell:
            conditions.append(f"""EXISTS (
                SELECT 1 FROM `tabItem Price` ip 
                WHERE ip.item_code = item.name 
                  AND ip.price_list = %(selling_price_list)s 
                  AND ip.price_list_rate > 0
                  AND {uom_valid_sql}
            )""")
            values["selling_price_list"] = target_sell
        elif target_buy:
            conditions.append(f"""EXISTS (
                SELECT 1 FROM `tabItem Price` ip 
                WHERE ip.item_code = item.name 
                  AND ip.price_list = %(buying_price_list)s 
                  AND ip.price_list_rate > 0
                  AND {uom_valid_sql}
            )""")
            values["buying_price_list"] = target_buy

    where_clause = " AND ".join(conditions)

    # 2. Fetch core items with pagination applied to the filtered result
    query = f"""
        SELECT 
            item.name,
            item.item_code,
            item.item_name,
            item.item_group,
            item.stock_uom AS default_uom,
            item.{hsn_field} AS hsn_code,
            item.standard_rate AS selling_rate,
            item.valuation_rate AS buying_rate
        FROM `tabItem` item
        WHERE {where_clause}
        ORDER BY item.item_name ASC
        LIMIT %(limit_page_length)s OFFSET %(limit_start)s
    """
    items = frappe.db.sql(query, values, as_dict=True)

    if not items:
        return []

    item_codes = [d.item_code for d in items]

    # 3. Bulk fetch Item Prices to override base rates
    item_prices = frappe.get_all(
        "Item Price",
        filters={"item_code": ["in", item_codes]},
        fields=["item_code", "price_list_rate", "selling", "buying", "price_list", "uom"]
    )
    
    prices_map = {}
    target_sell_lower = target_sell.lower() if target_sell else None
    target_buy_lower = target_buy.lower() if target_buy else None

    for ip in item_prices:
        if ip.item_code not in prices_map:
            prices_map[ip.item_code] = {"selling": {}, "buying": {}}
            
        # Match selling price list (case-insensitive)
        if target_sell_lower and str(ip.price_list).lower() == target_sell_lower:
            prices_map[ip.item_code]["selling"][ip.uom] = ip.price_list_rate
            
        # Match buying price list (case-insensitive)
        if target_buy_lower and str(ip.price_list).lower() == target_buy_lower:
            prices_map[ip.item_code]["buying"][ip.uom] = ip.price_list_rate

    # 4. Bulk fetch Multiple UOMs
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

    # 5. Bulk fetch Barcodes
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

    # 6. Bulk fetch Item Tax Templates
    tax_conditions = ["it.parent IN %(item_codes)s", "itt.disabled = 0"]
    tax_values = {"item_codes": item_codes}

    target_company = str(company).strip() if company and str(company).strip() else None
    if target_company:
        tax_conditions.append("itt.company = %(company)s")
        tax_values["company"] = target_company

    tax_query = f"""
        SELECT 
            it.parent AS item_code,
            it.item_tax_template,
            it.tax_category,
            itt.company,
            itt.gst_rate AS rate
        FROM `tabItem Tax` it
        JOIN `tabItem Tax Template` itt ON itt.name = it.item_tax_template
        WHERE {" AND ".join(tax_conditions)}
        ORDER BY it.idx ASC
    """
    item_taxes = frappe.db.sql(tax_query, tax_values, as_dict=True)

    tax_map = {}
    for t in item_taxes:
        tax_map.setdefault(t.item_code, []).append({
            "item_tax_template": t.item_tax_template,
            "company": t.company,
            "tax_category": t.tax_category,
            "rate": flt(t.rate)
        })

    # 7. Assemble final response
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

        # Attach Item Tax Templates
        item.item_tax_templates = tax_map.get(code, [])
        
        # Clean up temporary DB fields
        item.pop("name", None)

    # 8. Final safeguard: ensure uom_details strictly matches the criteria
    if not exact_item_code and (target_sell or target_buy):
        final_items = []
        for item in items:
            uom_list = item.get("uom_details", [])
            has_selling = any(flt(u.get("selling_rate", 0)) > 0 for u in uom_list)
            has_buying = any(flt(u.get("buying_rate", 0)) > 0 for u in uom_list)

            if target_sell and target_buy:
                if not (has_selling or has_buying):
                    continue
            elif target_sell:
                if not has_selling:
                    continue
            elif target_buy:
                if not has_buying:
                    continue

            final_items.append(item)

        return final_items

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

@frappe.whitelist()
def get_delivery_charge_item(selling_price_list=None):
    delivery_item = frappe.db.get_single_value("Cen CRM Settings", "delivery_charge_item")
    if not delivery_item:
        return []
        
    items = item_list(
        limit_start=1,
        limit_page_length=1,
        selling_price_list=selling_price_list,
        exact_item_code=delivery_item
    )
    
    # Remove buying_rate and barcodes from the result
    for item in items:
        item.pop("buying_rate", None)
        item.pop("barcodes", None)
        for uom in item.get("uom_details", []):
            if "buying_rate" in uom:
                del uom["buying_rate"]
                
    return items
