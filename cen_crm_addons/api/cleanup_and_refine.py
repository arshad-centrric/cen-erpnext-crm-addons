import frappe

def run():
    # 1. Clear duplicate/messy fields for Opportunity in BOTH Custom Field and DocField
    for fieldname in ["contact_mobile", "assigned_to_name"]:
        frappe.db.delete("Custom Field", {"dt": "Opportunity", "fieldname": fieldname})
        frappe.db.delete("DocField", {"parent": "Opportunity", "fieldname": fieldname})
    
    frappe.db.commit()
    
    # 2. Clear Meta Cache
    frappe.clear_cache(doctype="Opportunity")
    
    # 3. Run the refinement script
    from cen_crm_addons.api.list_view_refine import run as run_refine
    run_refine()
    
    print("Cleanup and Refinement Complete")

if __name__ == "__main__":
    run()
