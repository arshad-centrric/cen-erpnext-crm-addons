import frappe
import json
from frappe.utils import flt

@frappe.whitelist(allow_guest=False)
def get_stock_entry_list(search_term="", limit_start=1, limit_page_length=20):
    limit = int(limit_page_length)
    offset = max(0, int(limit_start) - 1)
    
    filters = {"stock_entry_type": "Repack"}
    if search_term:
        filters["name"] = ("like", f"%{search_term}%")
        
    stock_entries = frappe.get_all(
        "Stock Entry",
        filters=filters,
        fields=["name", "posting_date", "docstatus", "bom_no", "fg_completed_qty"],
        order_by="creation desc",
        limit_start=offset,
        limit_page_length=limit
    )
    
    return stock_entries

@frappe.whitelist(allow_guest=False)
def stock_entry_details(stock_entry_name):
    if not stock_entry_name:
        frappe.throw("stock_entry_name is required")
        
    se = frappe.get_doc("Stock Entry", stock_entry_name)
    
    details = {
        "name": se.name,
        "posting_date": se.posting_date,
        "bom_no": se.bom_no,
        "fg_completed_qty": se.fg_completed_qty,
        "docstatus": se.docstatus,
        "items": []
    }
    
    for item in se.items:
        details["items"].append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "qty": item.qty,
            "uom": item.uom,
            "s_warehouse": item.s_warehouse,
            "t_warehouse": item.t_warehouse
        })
        
    return details

@frappe.whitelist(allow_guest=False)
def get_item_boms(item_code, search_term="", limit_start=1, limit_page_length=20):
    if not item_code:
        frappe.throw("item_code is required")
        
    limit = int(limit_page_length)
    offset = max(0, int(limit_start) - 1)
    
    filters = {
        "item": item_code,
        "is_active": 1,
        "docstatus": 1
    }
    
    if search_term:
        filters["name"] = ("like", f"%{search_term}%")
        
    boms = frappe.get_all(
        "BOM",
        filters=filters,
        fields=["name", "quantity", "currency"],
        order_by="creation desc",
        limit_start=offset,
        limit_page_length=limit
    )
    
    return boms

@frappe.whitelist(allow_guest=False)
def get_bom_details(bom_name, production_qty=1):
    if not bom_name:
        frappe.throw("bom_name is required")
        
    bom = frappe.get_doc("BOM", bom_name)
    
    # If production_qty is empty string, default it to 1
    p_qty = flt(production_qty) if production_qty else 1.0
    multiplier = p_qty / flt(bom.quantity) if flt(bom.quantity) else 0
    
    items = []
    for item in bom.items:
        items.append({
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.uom,
            "required_qty": flt(item.qty) * multiplier
        })
        
    return items

@frappe.whitelist(allow_guest=False)
def create_bom(finished_product_code, production_qty, ingredients):
    import json
    try:
        if isinstance(ingredients, str):
            ingredients = frappe.parse_json(ingredients)
            
        if not ingredients:
            frappe.throw("Ingredients list cannot be empty")
            
        production_qty = flt(production_qty)
        if production_qty <= 0:
            frappe.throw("Production quantity must be greater than zero")
            
        bom = frappe.new_doc("BOM")
        bom.item = finished_product_code
        bom.quantity = production_qty
        bom.is_active = 1
        
        for ing in ingredients:
            bom.append("items", {
                "item_code": ing.get("item_code"),
                "qty": flt(ing.get("qty"))
            })
            
        bom.insert(ignore_permissions=True)
        bom.submit()
        
        return {
            "status": "success",
            "bom_name": bom.name,
            "message": "BOM created successfully"
        }
    except Exception as e:
        frappe.log_error(title="Mobile API Failed", message=frappe.get_traceback())
        frappe.local.response['http_status_code'] = 400
        return {"status": "error", "message": str(e)}

@frappe.whitelist(allow_guest=False)
def create_stock_entry(selected_bom, production_qty, source_warehouse, target_warehouse):
    try:
        if not selected_bom:
            frappe.throw("selected_bom is required")
            
        production_qty = flt(production_qty)
        if production_qty <= 0:
            frappe.throw("Production quantity must be greater than zero")
            
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Repack"
        se.purpose = "Repack"
        se.from_bom = 1
        se.bom_no = selected_bom
        se.fg_completed_qty = production_qty
        se.from_warehouse = source_warehouse
        se.to_warehouse = target_warehouse
        
        # Build consumption and generation grid based on the BOM
        se.get_items()
        
        se.insert(ignore_permissions=True)
        se.submit()
        
        return {
            "status": "success",
            "stock_entry": se.name,
            "message": "Stock Entry created successfully"
        }
    except Exception as e:
        frappe.log_error(title="Mobile API Failed", message=frappe.get_traceback())
        frappe.local.response['http_status_code'] = 400
        return {"status": "error", "message": str(e)}
