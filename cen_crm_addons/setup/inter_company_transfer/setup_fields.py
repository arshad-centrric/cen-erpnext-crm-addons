import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def create_inter_company_custom_fields():
    custom_fields = {
        "Customer": [
            {
                "fieldname": "custom_default_receiving_warehouse",
                "label": "Default Receiving Warehouse",
                "fieldtype": "Link",
                "options": "Warehouse",
                "insert_after": "represents_company",
                "depends_on": "eval:doc.is_internal_customer == 1"
            }
        ],
        "Supplier": [
            {
                "fieldname": "custom_default_buying_price_list",
                "label": "Default Buying Price List",
                "fieldtype": "Link",
                "options": "Price List",
                "insert_after": "represents_company",
                "depends_on": "eval:doc.is_internal_supplier == 1"
            }
        ]
    }
    
    create_custom_fields(custom_fields)
