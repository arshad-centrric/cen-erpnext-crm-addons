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
		<div class="container" style="max-width: 900px; margin-top: 20px;">
			<div class="row">
				<div class="col-md-6">
					<div style="padding-right: 15px;">
						<h5 class="text-muted">Mandatory Details</h5>
						<div class="form-group">
							<label class="control-label">Name <span class="text-danger">*</span></label>
							<input type="text" id="first_name" class="form-control" tabindex="1">
						</div>

						<div class="form-group">
							<label class="control-label">Mobile Number <span class="text-danger">*</span></label>
							<input type="text" id="mobile_no" class="form-control" tabindex="2">
						</div>

						<div class="form-group">
							<div class="assign-field" tabindex="3"></div>
						</div>

                        <div style="margin-top: 30px; text-align: center;">
                            <button class="btn btn-primary" id="create_all" style="min-width: 300px; font-weight: bold; height: 40px;">
                                Create
                            </button>
                            
                            <div id="whatsapp_container" style="margin-top: 20px; display: none;">
                                <a id="whatsapp_link" target="_blank" class="btn btn-outline-success">
                                    <i class="fa fa-whatsapp"></i> Chat on WhatsApp
                                </a>
                            </div>
                        </div>
					</div>
				</div>

				<div class="col-md-6">
					<div style="padding-left: 15px;">
						<h5 class="text-muted">Other Details</h5>
						<div class="form-group">
							<label class="control-label">Address</label>
							<input type="text" id="address_line1" class="form-control" tabindex="4">
						</div>

						<div class="form-group">
							<label class="control-label">City</label>
							<input type="text" id="city" class="form-control" tabindex="5">
						</div>

						<div class="form-group">
							<label class="control-label">State</label>
							<select id="state" class="form-control" tabindex="6">
								<option value="">Select State</option>
								${state_options}
							</select>
						</div>

						<div class="form-group">
							<label class="control-label">Pincode</label>
							<input type="text" id="pincode" class="form-control" tabindex="7">
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
            label: "Assign To",
            fieldname: "assign_to",
            fieldtype: "Link",
            options: "User",
            reqd: 0
        },
        render_input: true
    });

    // Combined Creation Logic
    $('#create_all').click(function () {
        let btn = $(this);
        
        // Handle "Add New" redirect/reload
        if (btn.text().trim() === __('Add New')) {
            location.reload();
            return;
        }

        let first_name = $('#first_name').val();
        let mobile = $('#mobile_no').val();
        let assign_to = assign_field.get_value();

        if (!first_name || !mobile || !assign_to) {
            frappe.msgprint(__("Name, Mobile Number, and Assigned To are mandatory."));
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
                    status: "Open"
                }
            },
            callback: function (r) {
                if (r.message) {
                    let lead_name = r.message.name;
                    let address_line1 = $('#address_line1').val();
                    let city = $('#city').val();
                    let state = $('#state').val();
                    let pincode = $('#pincode').val();

                    // 2. Create Address only if some info is provided
                    if (address_line1 || city) {
                        frappe.call({
                            method: "frappe.client.insert",
                            args: {
                                doc: {
                                    doctype: "Address",
                                    address_line1: address_line1 || "Not Provided",
                                    city: city || "Not Provided",
                                    state: state,
                                    pincode: pincode,
                                    links: [{
                                        link_doctype: "Lead",
                                        link_name: lead_name
                                    }]
                                }
                            }
                        });
                    }

                    // 3. Assign Lead
                    frappe.call({
                        method: "frappe.desk.form.assign_to.add",
                        args: {
                            assign_to: [assign_to],
                            doctype: "Lead",
                            name: lead_name,
                            description: "Auto-Assigned from Quick Entry"
                        }
                    });

                    // 4. Create & Insert Opportunity
                    frappe.call({
                        method: "erpnext.crm.doctype.lead.lead.make_opportunity",
                        args: {
                            source_name: lead_name
                        },
                        callback: function (res) {
                            if (res.message) {
                                let opportunity_doc = res.message;
                                opportunity_doc.doctype = "Opportunity"; // Ensure doctype is present

                                frappe.call({
                                    method: "frappe.client.insert",
                                    args: {
                                        doc: opportunity_doc
                                    },
                                    callback: function (final_res) {
                                        btn.prop('disabled', false).text(__('Add New'));
                                        if (final_res.message) {
                                            // Show WhatsApp link
                                            let formatted_mobile = mobile.replace(/\D/g, '');
                                            if (formatted_mobile.length === 10) {
                                                formatted_mobile = '91' + formatted_mobile;
                                            }

                                            $('#whatsapp_link').attr('href', `https://wa.me/${formatted_mobile}`);
                                            $('#whatsapp_container').show();
                                        }
                                    }
                                });
                            } else {
                                btn.prop('disabled', false).text(__('Add New'));
                            }
                        }
                    });
                } else {
                    btn.prop('disabled', false).text(__('Create'));
                }
            }
        });
    });

};