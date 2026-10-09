import frappe
from frappe.contacts.doctype.address.address import get_default_address, render_address

def get_company_address_list(company):
    """Returns the active Addresses linked to a Company, default address first."""
    fields = [
        "name", "address_title", "address_type", "address_line1", "address_line2",
        "city", "state", "pincode", "country"
    ]
    if frappe.get_meta("Address").has_field("gstin"):
        fields.append("gstin")

    addresses = frappe.get_all(
        "Address",
        filters=[
            ["Dynamic Link", "link_doctype", "=", "Company"],
            ["Dynamic Link", "link_name", "=", company],
            ["disabled", "=", 0]
        ],
        fields=fields,
        order_by="`tabAddress`.address_title asc",
        distinct=True
    )

    default_address = get_default_address("Company", company)

    for address in addresses:
        address.is_default = 1 if address.name == default_address else 0
        address.display = render_address(address.name, check_permissions=False)

    addresses.sort(key=lambda address: -address.is_default)
    return addresses

def validate_company_address(address, company):
    """Ensures the Address is active and linked to the Company. Returns the Address name."""
    address = str(address).strip()

    address_details = frappe.db.get_value("Address", address, ["name", "disabled"], as_dict=True)
    if not address_details:
        frappe.throw(f"Company Address {address} not found")

    if address_details.disabled:
        frappe.throw(f"Company Address {address} is disabled")

    is_company_address = frappe.db.exists("Dynamic Link", {
        "parenttype": "Address",
        "parent": address_details.name,
        "link_doctype": "Company",
        "link_name": company
    })
    if not is_company_address:
        frappe.throw(f"Address {address} is not linked to company {company}")

    return address_details.name
