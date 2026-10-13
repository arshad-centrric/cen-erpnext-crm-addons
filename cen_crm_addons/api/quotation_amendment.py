import frappe

LOCATION_FIELDS = [
    "delivery_label", "custom_delivery_store", "custom_mode_of_delivery",
    "custom_delivery_partner", "custom_delivery_date", "custom_delivery_time",
    "custom_address_line_1", "custom_address_line_2", "custom_delivery_city",
    "custom_delivery_state", "custom_pincode", "custom_delivery_country",
    "custom_delivery_contact"
]

def get_quotation_to_amend(amended_from, opportunity_id):
    """Validates that a Quotation can be amended for the Opportunity and returns it."""
    amended_from = str(amended_from).strip()

    if not frappe.db.exists("Quotation", amended_from):
        frappe.throw(f"Quotation {amended_from} not found")

    source = frappe.get_doc("Quotation", amended_from)

    if source.docstatus != 2:
        frappe.throw(f"Quotation {amended_from} must be cancelled before it can be amended")

    if source.opportunity != opportunity_id:
        frappe.throw(f"Quotation {amended_from} does not belong to Opportunity {opportunity_id}")

    existing_amendment = frappe.db.get_value(
        "Quotation", {"amended_from": amended_from, "docstatus": ("!=", 2)}, "name"
    )
    if existing_amendment:
        frappe.throw(f"Quotation {amended_from} is already amended as {existing_amendment}")

    return source

def get_amendment_defaults(source):
    """Values of the cancelled Quotation, used for anything the amendment payload leaves out."""
    return frappe._dict(
        items=[
            {
                "item_code": row.item_code,
                "qty": row.qty,
                "rate": row.rate,
                "uom": row.uom,
                "warehouse": row.warehouse
            }
            for row in source.get("items", [])
        ],
        delivery_locations=[
            {fieldname: row.get(fieldname) for fieldname in LOCATION_FIELDS}
            for row in source.get("custom_location_details", [])
        ],
        selling_price_list=source.selling_price_list,
        customer=source.party_name if source.quotation_to == "Customer" else None,
        company_address=source.company_address,
        packing_instructions=source.get("custom_packing_instructions")
    )
