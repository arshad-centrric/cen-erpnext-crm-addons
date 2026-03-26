import frappe

def after_install():
    # 1. Add "To Be Quoted" Sales Stage
    stage = "To Be Quoted"
    if not frappe.db.exists("Sales Stage", stage):
        s = frappe.new_doc("Sales Stage")
        s.stage_name = stage
        s.insert(ignore_permissions=True)
        
    # 2. Add sales_stage to standard filters in Opportunity List
    frappe.make_property_setter({
        "doctype_or_field": "DocField",
        "doc_type": "Opportunity",
        "field_name": "sales_stage",
        "property": "in_standard_filter",
        "property_type": "Check",
        "value": "1"
    })
    
    frappe.db.commit()

def run_now():
    frappe.init(site="crm.test")
    frappe.connect()
    after_install()
    print("Setup complete")

if __name__ == "__main__":
    run_now()
