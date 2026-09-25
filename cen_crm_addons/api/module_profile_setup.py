import frappe

def setup_module_profiles():
    """
    Creates or updates Module Profiles to restrict UI access for Sales roles.
    Uses an AGGRESSIVE "Allow-List" approach to hide all non-essential modules.
    """
    profiles = [
        {
            "name": "Sales Staff Profile",
            # FIXED: Added "cen_crm_addons" to exactly match the database Module Def
            "allowed": ["Cen Crm Addons"]
        },
        {
            "name": "Sales Supervisor Profile",
            # FIXED: Added "cen_crm_addons" here as well
            "allowed": ["Cen Crm Addons"]
        }
    ]

    # Fetch all available modules in the system
    all_modules = frappe.get_all("Module Def", pluck="name")

    for p in profiles:
        # Determine which modules to block (everything NOT in the allow-list)
        blocked_modules = [m for m in all_modules if m not in p["allowed"]]
        
        create_or_update_profile(p["name"], blocked_modules)

def create_or_update_profile(profile_name, blocked_modules):
    """
    Internal helper to safely create or update a Module Profile.
    Clears existing block_modules to ensure the "Allow-List" logic is fully applied.
    """
    if frappe.db.exists("Module Profile", profile_name):
        doc = frappe.get_doc("Module Profile", profile_name)
    else:
        doc = frappe.new_doc("Module Profile")
        doc.module_profile_name = profile_name
    
    # Aggressively reset child table to ensure only allowed modules are visible
    doc.set("block_modules", [])
    
    for m in blocked_modules:
        doc.append("block_modules", {
            "module": m
        })
    
    doc.save(ignore_permissions=True)
    frappe.db.commit()