import frappe
from frappe.contacts.doctype.address.address import get_default_address, render_address

# Fields added by cen_branch_management: an Address says which Branch it belongs to,
# and a Branch points to its own default Address.
ADDRESS_BRANCH_FIELD = "custom_cen_address_branch"
BRANCH_ADDRESS_FIELD = "custom_cen_branch_address"

def get_company_address_list(company, branch=None):
    """
    Returns the active Addresses linked to a Company, default address first.
    With a branch, only the addresses of that Branch are returned (same rule as the desk forms).
    """
    fields = [
        "name", "address_title", "address_type", "address_line1", "address_line2",
        "city", "state", "pincode", "country"
    ]
    address_meta = frappe.get_meta("Address")
    if address_meta.has_field("gstin"):
        fields.append("gstin")

    has_branch_field = address_meta.has_field(ADDRESS_BRANCH_FIELD)
    if has_branch_field:
        fields.append(f"{ADDRESS_BRANCH_FIELD} as branch")

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

    if branch and has_branch_field:
        branch_address = get_branch_default_address(branch, company)
        addresses = [a for a in addresses if a.branch == branch or a.name == branch_address]
        default_address = branch_address or default_address

    for address in addresses:
        address.is_default = 1 if address.name == default_address else 0
        address.display = render_address(address.name, check_permissions=False)

    addresses.sort(key=lambda address: -address.is_default)
    return addresses

def get_branch_default_address(branch, company):
    """Returns the Branch Address of a Branch if it is active and linked to the Company (or None)."""
    if not branch or not frappe.get_meta("Branch").has_field(BRANCH_ADDRESS_FIELD):
        return None

    address = frappe.db.get_value("Branch", branch, BRANCH_ADDRESS_FIELD)
    if not address or frappe.db.get_value("Address", address, "disabled"):
        return None

    return address if _is_company_address(address, company) else None

def validate_company_address(address, company, branch=None):
    """
    Ensures the Address is active and linked to the Company. Returns the Address name.
    With a branch, an Address that belongs to a different Branch is rejected.
    """
    address = str(address).strip()

    fields = ["name", "disabled"]
    has_branch_field = frappe.get_meta("Address").has_field(ADDRESS_BRANCH_FIELD)
    if has_branch_field:
        fields.append(f"{ADDRESS_BRANCH_FIELD} as branch")

    address_details = frappe.db.get_value("Address", address, fields, as_dict=True)
    if not address_details:
        frappe.throw(f"Company Address {address} not found")

    if address_details.disabled:
        frappe.throw(f"Company Address {address} is disabled")

    if not _is_company_address(address_details.name, company):
        frappe.throw(f"Address {address} is not linked to company {company}")

    if branch and has_branch_field and address_details.branch and address_details.branch != branch:
        frappe.throw(f"Address {address} belongs to branch {address_details.branch}, not {branch}")

    return address_details.name

def _is_company_address(address, company):
    return bool(frappe.db.exists("Dynamic Link", {
        "parenttype": "Address",
        "parent": address,
        "link_doctype": "Company",
        "link_name": company
    }))
