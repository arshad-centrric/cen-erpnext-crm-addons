import frappe

GODOWN_ROLE = "AGT - Godown"
GODOWN_DESK = "Godown Desk"


def extend_bootinfo(bootinfo):
    """
    Limits the desk launcher (apps screen) and sidebars for Godown users to the
    Godown Desk. Permissions are still enforced by the role itself; this only
    decides which icons are shown. System Managers always see everything.
    """
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return

    roles = set(frappe.get_roles(user))
    if GODOWN_ROLE not in roles or "System Manager" in roles:
        return

    bootinfo.desktop_icons = [
        icon for icon in (bootinfo.get("desktop_icons") or [])
        if icon.get("label") == GODOWN_DESK or icon.get("parent_icon") == GODOWN_DESK
    ]

    sidebars = bootinfo.get("workspace_sidebar_item") or {}
    bootinfo.workspace_sidebar_item = {
        key: value for key, value in sidebars.items()
        if key == GODOWN_DESK.lower() or key == "my workspaces"
    }
