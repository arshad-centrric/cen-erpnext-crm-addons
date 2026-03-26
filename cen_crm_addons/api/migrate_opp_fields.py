import frappe
from cen_crm_addons.api.crm_permissions import sync_opportunity_list_fields

def run():
    opportunities = frappe.get_all("Opportunity")
    print(f"Syncing {len(opportunities)} opportunities...")
    for opp in opportunities:
        try:
            doc = frappe.get_doc("Opportunity", opp.name)
            sync_opportunity_list_fields(doc)
            doc.save(ignore_permissions=True)
            frappe.db.commit()
        except Exception as e:
            print(f"Error syncing {opp.name}: {e}")

    
    print("Migration Complete")

if __name__ == "__main__":
    run()
