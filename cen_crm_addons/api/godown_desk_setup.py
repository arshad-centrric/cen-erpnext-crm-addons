import json

import frappe

ROLE = "AGT - Godown"
DESK = "Godown Desk"
MODULE = "Cen Crm Addons"
ICON = "stock"

# (label, doctype, route_options)
DESK_ITEMS = [
    ("Sales Order", "Sales Order", None),
    ("Sales Invoice", "Sales Invoice", None),
    ("GRN", "Purchase Receipt", None),
    ("Stock Transfer", "Stock Entry", {"stock_entry_type": "Material Transfer"}),
]


def setup_godown_desk():
    """
    Creates the 'Godown Desk' workspace, sidebar and launcher icon holding only
    the documents the AGT - Godown role works with. Safe to run repeatedly.
    """
    if not frappe.db.exists("Role", ROLE):
        return

    _setup_workspace()
    _setup_sidebar()
    _setup_desktop_icon()

    frappe.db.commit()
    frappe.clear_cache()


def _setup_workspace():
    content = [{"id": "godown_hdr", "type": "header",
                "data": {"text": f'<span class="h4">{DESK}</span>', "col": 12}}]
    shortcuts = []
    for idx, (label, doctype, route_options) in enumerate(DESK_ITEMS):
        content.append({"id": f"godown_sc{idx}", "type": "shortcut",
                        "data": {"shortcut_name": label, "col": 3}})
        shortcuts.append({
            "type": "DocType",
            "link_to": doctype,
            "label": label,
            "doc_view": "List",
            "color": "Grey",
            "stats_filter": json.dumps(route_options) if route_options else "[]",
        })

    if frappe.db.exists("Workspace", DESK):
        doc = frappe.get_doc("Workspace", DESK)
    else:
        doc = frappe.new_doc("Workspace")
        doc.name = DESK
        doc.label = DESK
        doc.title = DESK

    doc.module = MODULE
    doc.public = 1
    doc.icon = ICON
    doc.content = json.dumps(content)
    doc.set("shortcuts", shortcuts)
    doc.set("roles", [{"role": ROLE}])
    doc.save(ignore_permissions=True)


def _setup_sidebar():
    items = [{"label": "Home", "type": "Link", "link_type": "Workspace", "link_to": DESK}]
    for label, doctype, route_options in DESK_ITEMS:
        item = {"label": label, "type": "Link", "link_type": "DocType", "link_to": doctype}
        if route_options:
            item["route_options"] = json.dumps(route_options)
        items.append(item)

    if frappe.db.exists("Workspace Sidebar", DESK):
        doc = frappe.get_doc("Workspace Sidebar", DESK)
    else:
        doc = frappe.new_doc("Workspace Sidebar")
        doc.title = DESK

    doc.header_icon = ICON
    doc.module = MODULE
    doc.set("items", items)
    doc.save(ignore_permissions=True)


def _setup_desktop_icon():
    if frappe.db.exists("Desktop Icon", DESK):
        doc = frappe.get_doc("Desktop Icon", DESK)
    else:
        doc = frappe.new_doc("Desktop Icon")
        doc.label = DESK

    doc.icon_type = "Link"
    doc.link_type = "Workspace Sidebar"
    doc.link_to = DESK
    doc.icon = ICON
    doc.bg_color = "gray"
    doc.hidden = 0
    doc.standard = 0
    # System Manager keeps it visible for admins who manage the desk
    doc.set("roles", [{"role": ROLE}, {"role": "System Manager"}])
    doc.save(ignore_permissions=True)
