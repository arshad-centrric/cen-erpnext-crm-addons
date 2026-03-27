frappe.pages['quick-lead-entry'].on_page_load = function (wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Quick Lead Entry',
        single_column: true
    });

    // Add List Buttons at top right
    page.add_inner_button(__('Lead List'), function () {
        frappe.set_route('List', 'Lead');
    });

    page.add_inner_button(__('Opportunity List'), function () {
        frappe.set_route('List', 'Opportunity');
    });

    // India States
    const states = [
        "Kerala", "Tamil Nadu", "Karnataka", "Andhra Pradesh", "Telangana",
        "Maharashtra", "Gujarat", "Rajasthan", "Madhya Pradesh", "Uttar Pradesh",
        "Bihar", "West Bengal", "Odisha", "Punjab", "Haryana", "Delhi",
        "Himachal Pradesh", "Uttarakhand", "Jharkhand", "Chhattisgarh",
        "Assam", "Goa", "Tripura", "Meghalaya", "Manipur", "Nagaland",
        "Arunachal Pradesh", "Sikkim"
    ];

    let state_options = states.map(s => `<option value="${s}">${s}</option>`).join("");

    // UI Layout
    $(wrapper).find('.layout-main-section').html(`
		<div class="container" style="max-width: 600px; margin-top: 30px; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h4 class="text-center" style="margin-bottom: 25px; color: #1a1a1a; font-weight: 600;">New CRM Entry</h4>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="form-group">
                        <label class="control-label" style="font-weight: 500;">Customer Name <span class="text-danger">*</span></label>
                        <input type="text" id="first_name" class="form-control" tabindex="1" placeholder="Enter Full Name">
                    </div>

                    <div class="form-group">
                        <label class="control-label" style="font-weight: 500;">Mobile Number <span class="text-danger">*</span></label>
                        <input type="text" id="mobile_no" class="form-control" tabindex="2" placeholder="e.g. 9876543210">
                    </div>

                    <div class="form-group">
                        <div class="assign-field" tabindex="3"></div>
                    </div>

                    <hr style="margin: 25px 0;">

                    <div class="row">
                        <div class="col-6">
                            <div class="form-group">
                                <label class="control-label" style="font-weight: 500;">City</label>
                                <input type="text" id="city" class="form-control" tabindex="4" placeholder="City">
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="form-group">
                                <label class="control-label" style="font-weight: 500;">State</label>
                                <select id="state" class="form-control" tabindex="5">
                                    <option value="">Select State</option>
                                    ${state_options}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 35px; text-align: center;">
                        <button class="btn btn-primary btn-lg" id="create_all" style="width: 100%; font-weight: bold; border-radius: 6px; background-color: #2491ff; border: none; padding: 12px 0;">
                            Create & Assign
                        </button>
                        
                        <div id="whatsapp_container" style="margin-top: 20px; display: none;">
                            <a id="whatsapp_link" target="_blank" class="btn btn-outline-success" style="width: 100%; border-color: #25D366; color: #25D366; font-weight: bold; padding: 10px 0;">
                                <i class="fa fa-whatsapp"></i> Chat on WhatsApp
                            </a>
                        </div>
                    </div>
                </div>
            </div>
		</div>
	`);

    // 🔹 Modern Assign Field (ERPNext style)
    let assign_field = frappe.ui.form.make_control({
        parent: $(wrapper).find('.assign-field'),
        df: {
            label: "Assign Sales Person",
            fieldname: "assign_to",
            fieldtype: "Link",
            options: "User",
            reqd: 0,
            placeholder: "Select Sales Team Member"
        },
        render_input: true
    });

    // Combined Creation Logic
    $('#create_all').click(function () {
        let btn = $(this);
        
        if (btn.text().trim() === __('Add New')) {
            location.reload();
            return;
        }

        let first_name = $('#first_name').val();
        let mobile = $('#mobile_no').val();
        let assign_to = assign_field.get_value();
        let city = $('#city').val();
        let state = $('#state').val();

        if (!first_name || !mobile || !assign_to) {
            frappe.msgprint(__("Name, Mobile Number, and Assigned Person are mandatory."));
            return;
        }

        btn.prop('disabled', true).text(__('Creating...'));

        // 1. Create Lead
        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Lead",
                    first_name: first_name,
                    mobile_no: mobile,
                    phone: mobile,
                    city: city,
                    state: state,
                    status: "Open"
                }
            },
            callback: function (r) {
                if (r.message) {
                    let lead_name = r.message.name;

                    // 2. Assign Lead
                    frappe.call({
                        method: "frappe.desk.form.assign_to.add",
                        async: false,
                        args: {
                            assign_to: [assign_to],
                            doctype: "Lead",
                            name: lead_name,
                            description: "Auto-Assigned from Quick Entry"
                        }
                    });

                    // 3. Create & Insert Opportunity
                    frappe.call({
                        method: "erpnext.crm.doctype.lead.lead.make_opportunity",
                        args: {
                            source_name: lead_name
                        },
                        callback: function (res) {
                            if (res.message) {
                                let opportunity_doc = res.message;
                                opportunity_doc.doctype = "Opportunity";

                                frappe.call({
                                    method: "frappe.client.insert",
                                    args: {
                                        doc: opportunity_doc
                                    },
                                    callback: function (final_res) {
                                        if (final_res.message) {
                                            let opp_name = final_res.message.name;

                                            // 4. Assign Opportunity (Ground Truth for Sales Team)
                                            frappe.call({
                                                method: "frappe.desk.form.assign_to.add",
                                                args: {
                                                    assign_to: [assign_to],
                                                    doctype: "Opportunity",
                                                    name: opp_name,
                                                    description: "Lead Assigned: " + first_name
                                                }
                                            });

                                            btn.prop('disabled', false).text(__('Add New')).removeClass('btn-primary').addClass('btn-secondary');
                                            
                                            // Show WhatsApp link
                                            let formatted_mobile = mobile.replace(/\D/g, '');
                                            if (formatted_mobile.length === 10) formatted_mobile = '91' + formatted_mobile;

                                            $('#whatsapp_link').attr('href', `https://wa.me/${formatted_mobile}`);
                                            $('#whatsapp_container').fadeIn();
                                            
                                            frappe.show_alert({
                                                message: __('Lead and Opportunity created successfully!'),
                                                indicator: 'green'
                                            });
                                        }
                                    }
                                });
                            } else {
                                btn.prop('disabled', false).text(__('Create & Assign'));
                            }
                        }
                    });
                } else {
                    btn.prop('disabled', false).text(__('Create & Assign'));
                }
            }
        });
    });

};