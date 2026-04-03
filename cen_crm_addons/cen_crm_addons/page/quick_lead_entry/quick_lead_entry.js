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
        "Maharashtra", "Gujarat", "Rajasthan", "Mudhya Pradesh", "Uttar Pradesh",
        "Bihar", "West Bengal", "Odisha", "Punjab", "Haryana", "Delhi",
        "Himachal Pradesh", "Uttarakhand", "Jharkhand", "Chhattisgarh",
        "Assam", "Goa", "Tripura", "Meghalaya", "Manipur", "Nagaland",
        "Arunachal Pradesh", "Sikkim"
    ];

    let state_options = states.map(s => `<option value="${s}">${s}</option>`).join("");

    // UI Layout
    $(wrapper).find('.layout-main-section').html(`
        <div class="container" style="max-width: 600px; margin-top: 20px;">
            <div class="row justify-content-center">
                <div class="col-md-12">
                    <div style="padding: 15px; background-color: var(--bg-color); border-radius: 8px; border: 1px solid var(--border-color);">
                        <h5 class="text-muted" style="margin-bottom: 20px;">Main Details</h5>
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
                            <button class="btn btn-primary" id="create_all" style="width: 100%; font-weight: bold; height: 40px;">
                                Create
                            </button>
                            
                            <div id="whatsapp_container" style="margin-top: 20px; display: none;">
                                <a id="whatsapp_link" target="_blank" class="btn btn-outline-success" style="width: 100%;">
                                    <i class="fa fa-whatsapp"></i> Chat on WhatsApp
                                </a>
                            </div>
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

        // 🔹 Generate WhatsApp Link upfront
        let formatted_mobile = mobile.replace(/\D/g, '');
        if (formatted_mobile.length === 10) {
            formatted_mobile = '91' + formatted_mobile;
        }
        let wa_link = `https://wa.me/${formatted_mobile}`;

        btn.prop('disabled', true).text(__('Creating...'));

        // 1. Create Lead with Custom Fields
        frappe.call({
            method: "frappe.client.insert",
            args: {
                doc: {
                    doctype: "Lead",
                    first_name: first_name,
                    mobile_no: mobile,
                    status: "Open",
                    custom_assigned_to: assign_to,
                    custom_wa_chat_link: wa_link
                }
            },
            callback: function (r) {
                if (r.message) {
                    let lead_name = r.message.name;

                    // 2. Assign Lead via ToDo (Required for system notifications/sidebar)
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
                                opportunity_doc.doctype = "Opportunity"; 
                                
                                // Mapping fields explicitly
                                opportunity_doc.contact_mobile = mobile;
                                opportunity_doc.custom_assigned_to = assign_to;
                                opportunity_doc.custom_wa_chat_link = wa_link;

                                frappe.call({
                                    method: "frappe.client.insert",
                                    args: {
                                        doc: opportunity_doc
                                    },
                                    callback: function (final_res) {
                                        btn.prop('disabled', false).text(__('Add New'));
                                        if (final_res.message) {
                                            // Show WhatsApp link
                                            $('#whatsapp_link').attr('href', wa_link);
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