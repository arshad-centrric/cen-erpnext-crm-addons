frappe.pages['quick-lead-entry'].on_page_load = function(wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Quick Lead Entry',
        single_column: true
    });

    // India States
    const states = [
        "Kerala","Tamil Nadu","Karnataka","Andhra Pradesh","Telangana",
        "Maharashtra","Gujarat","Rajasthan","Madhya Pradesh","Uttar Pradesh",
        "Bihar","West Bengal","Odisha","Punjab","Haryana","Delhi",
        "Himachal Pradesh","Uttarakhand","Jharkhand","Chhattisgarh",
        "Assam","Goa","Tripura","Meghalaya","Manipur","Nagaland",
        "Arunachal Pradesh","Sikkim"
    ];

    let state_options = states.map(s => `<option value="${s}">${s}</option>`).join("");

    // UI Layout
    $(wrapper).html(`
        <div class="container" style="max-width: 500px; margin-top: 20px;">
            
            <h4>Basic Details</h4>

            <div class="form-group">
                <label>First Name</label>
                <input type="text" id="first_name" class="form-control">
            </div>

            <div class="form-group">
                <label>Mobile Number</label>
                <input type="text" id="mobile_no" class="form-control">
            </div>

            <hr>

            <h5>Address Details</h5>

            <div class="form-group">
                <label>Address Line 1</label>
                <textarea id="address_line1" class="form-control"></textarea>
            </div>

            <div class="form-group">
                <label>City</label>
                <input type="text" id="city" class="form-control">
            </div>

            <div class="form-group">
                <label>State</label>
                <select id="state" class="form-control">
                    <option value="">Select State</option>
                    ${state_options}
                </select>
            </div>

            <div class="form-group">
                <label>Pincode</label>
                <input type="text" id="pincode" class="form-control">
            </div>

            <hr>

            <h5>Assign</h5>
            <div class="form-group assign-field"></div>

            <button class="btn btn-primary" id="create_lead">
                Create Lead
            </button>

            <hr>

            <button class="btn btn-success" id="create_opportunity" style="display:none;">
                Create Opportunity
            </button>

        </div>
    `);

    // 🔹 Modern Assign Field (ERPNext style)
    let assign_field = frappe.ui.form.make_control({
        parent: $(wrapper).find('.assign-field'),
        df: {
            label: "Assign To",
            fieldname: "assign_to",
            fieldtype: "Link",
            options: "User"
        },
        render_input: true
    });

    // Default to current user
    assign_field.set_value(frappe.session.user);

    let created_lead = null;

    // Create Lead
    $('#create_lead').click(function() {

        let first_name = $('#first_name').val();
        let mobile = $('#mobile_no').val();

        if (!first_name || !mobile) {
            frappe.msgprint("First Name and Mobile are required");
            return;
        }

        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Lead",
                    first_name: first_name,
                    mobile_no: mobile,
                    phone: mobile
                }
            },
            callback: function(r) {
                if (r.message) {

                    created_lead = r.message.name;

                    // Create Address (ERPNext standard way)
                    frappe.call({
                        method: "frappe.client.insert",
                        args: {
                            doc: {
                                doctype: "Address",
                                address_line1: $('#address_line1').val(),
                                city: $('#city').val(),
                                state: $('#state').val(),
                                pincode: $('#pincode').val(),
                                links: [{
                                    link_doctype: "Lead",
                                    link_name: created_lead
                                }]
                            }
                        }
                    });

                    // Assign Lead
                    let assign_to = assign_field.get_value();

                    if (assign_to) {
                        frappe.call({
                            method: "frappe.desk.form.assign_to.add",
                            args: {
                                assign_to: [assign_to],
                                doctype: "Lead",
                                name: created_lead,
                                description: "New Lead Assigned"
                            }
                        });
                    }

                    frappe.msgprint("Lead Created: " + created_lead);

                    $('#create_opportunity').show();
                }
            }
        });
    });

    // Create Opportunity
    $('#create_opportunity').click(function() {

        if (!created_lead) {
            frappe.msgprint("Create Lead first");
            return;
        }

        frappe.call({
            method: "erpnext.crm.doctype.lead.lead.make_opportunity",
            args: {
                source_name: created_lead
            },
            callback: function(r) {
                if (r.message) {
                    frappe.set_route("Form", "Opportunity", r.message.name);
                }
            }
        });
    });

};