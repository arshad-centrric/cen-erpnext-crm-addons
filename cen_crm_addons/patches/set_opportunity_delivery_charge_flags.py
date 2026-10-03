import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """Backfills the Delivery Charge flags on existing Opportunities."""
    # Patches run before fixtures are synced, so make sure the columns exist first.
    # The fixture (custom_field.json) remains the source of truth for these fields.
    create_custom_fields({
        "Opportunity": [
            {
                "fieldname": "custom_has_delivery_charge",
                "label": "Has Delivery Charge",
                "fieldtype": "Check",
                "insert_after": "items",
                "default": "0",
                "read_only": 1
            }
        ],
        "Opportunity Item": [
            {
                "fieldname": "custom_is_delivery_charge",
                "label": "Is Delivery Charge",
                "fieldtype": "Check",
                "insert_after": "custom_view_bundle",
                "default": "0",
                "read_only": 1
            }
        ]
    })

    delivery_item = frappe.db.get_single_value("Cen CRM Settings", "delivery_charge_item")
    if not delivery_item:
        return

    frappe.db.sql("""
        UPDATE `tabOpportunity Item`
        SET custom_is_delivery_charge = 1
        WHERE parenttype = 'Opportunity' AND item_code = %s
    """, (delivery_item,))

    frappe.db.sql("""
        UPDATE `tabOpportunity`
        SET custom_has_delivery_charge = 1
        WHERE name IN (
            SELECT parent FROM `tabOpportunity Item`
            WHERE parenttype = 'Opportunity' AND item_code = %s
        )
    """, (delivery_item,))
