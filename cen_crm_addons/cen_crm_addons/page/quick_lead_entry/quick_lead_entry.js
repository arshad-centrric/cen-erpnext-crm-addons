frappe.pages['quick-lead-entry'].on_page_load = function (wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Quick Lead Entry',
        single_column: true
    });

    // Add List Buttons at top right
    // page.add_inner_button(__('Lead List'), function () {
    //     frappe.set_route('List', 'Lead');
    // });

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
                            <label class="control-label">Mobile Number <span class="text-danger">*</span></label>
                            <input type="text" id="mobile_no" class="form-control awesomplete" tabindex="1" autocomplete="off">
                            <div class="d-flex justify-content-between align-items-center mt-1">
                                <small class="form-text text-muted" id="customer_hint" style="display:none; color: green !important; margin-top: 0;">Existing Customer Found!</small>
                                <button class="btn btn-xs btn-default" id="btn_view_history" style="display:none; border-color: var(--border-color); font-weight: 500; font-size: 11px;">View History</button>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="control-label">Name <span class="text-danger">*</span></label>
                            <input type="text" id="first_name" class="form-control" tabindex="2">
                        </div>

                        <div class="form-group">
                            <div class="assign-field" tabindex="3"></div>
                        </div>

                        <div class="form-group">
                            <label class="control-label">Remarks</label>
                            <textarea id="notes" class="form-control" tabindex="4" rows="3" style="resize: vertical;"></textarea>
                        </div>

                        <div style="margin-top: 30px; text-align: center;">
                            <button class="btn btn-primary" id="create_all" style="width: 100%; font-weight: bold; height: 40px;" tabindex="5">
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

    // 🔹 Modern Assign Field (ERPNext style) - UPDATED WITH ROLE FILTER
    let assign_field = frappe.ui.form.make_control({
        parent: $(wrapper).find('.assign-field'),
        df: {
            label: "Assign To",
            fieldname: "assign_to",
            fieldtype: "Link",
            options: "User",
            reqd: 0,
            get_query: function () {
                return { query: "cen_crm_addons.api.queries.get_sales_persons" };
            }
        },
        render_input: true
    });

    // 🔹 Initialize Awesomplete for Mobile Number
    let mobile_input = $(wrapper).find('#mobile_no')[0];
    let existing_customer_id = null;
    
    let awesomplete = new Awesomplete(mobile_input, {
        minChars: 3,
        maxItems: 10,
        autoFirst: true,
        filter: function(text, input) { return true; } // Bypass default filter, we filter on server
    });

    $(mobile_input).on('input', frappe.utils.debounce(function() {
        let txt = $(this).val();
        existing_customer_id = null;
        $('#customer_hint').hide();
        $('#btn_view_history').hide();
        $('#first_name').prop('readonly', false);

        if(txt.length >= 3) {
            frappe.call({
                method: "cen_crm_addons.cen_crm_addons.page.quick_lead_entry.search_customers_by_phone",
                args: { txt: txt },
                callback: function(r) {
                    if(r.message && r.message.length > 0) {
                        let list = r.message.map(row => {
                            return {
                                label: row.mobile_no + " - " + row.customer_name,
                                value: row.mobile_no,
                                customer_name: row.customer_name,
                                name: row.name
                            };
                        });
                        awesomplete.list = list;
                    } else {
                        awesomplete.list = [];
                    }
                }
            });
        }
    }, 500));

    $(mobile_input).on('awesomplete-selectcomplete', function(e) {
        let selected_item = awesomplete.get_item(e.originalEvent.text.value);
        if (selected_item) {
            existing_customer_id = selected_item.name;
            $('#first_name').val(selected_item.customer_name).prop('readonly', true);
            $('#customer_hint').show();
            $('#btn_view_history').show();
        }
    });

    // Handle View History Click
    $(wrapper).on('click', '#btn_view_history', function() {
        let mobile = $('#mobile_no').val();
        if (!mobile) return;

        let d = new frappe.ui.Dialog({
            title: __('Opportunity History'),
            size: 'large',
            fields: [
                {
                    fieldtype: 'HTML',
                    fieldname: 'history_html'
                }
            ]
        });

        d.show();
        d.set_df_property('history_html', 'options', '<div class="text-center" style="padding: 30px;"><i class="fa fa-spinner fa-spin text-muted" style="font-size: 24px;"></i></div>');

        frappe.call({
            method: "cen_crm_addons.cen_crm_addons.page.quick_lead_entry.get_opportunity_history_by_phone",
            args: { mobile_no: mobile },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let html = '<div class="list-group" style="margin-bottom: 0;">';
                    r.message.forEach(opp => {
                        let status_color = opp.status === 'Open' ? 'orange' : (opp.status === 'Quotation' ? 'blue' : (opp.status === 'Converted' ? 'green' : 'gray'));
                        
                        let assigned_person = opp.custom_assigned_full_name || opp.custom_assigned_to || 'Unassigned';
                        let date = frappe.datetime.str_to_user(opp.creation).split(' ')[0]; // Just the date

                        html += `
                            <a href="/app/opportunity/${opp.name}" target="_blank" class="list-group-item list-group-item-action" style="padding: 15px; border-radius: 6px; margin-bottom: 8px; border: 1px solid var(--border-color);">
                                <div class="d-flex w-100 justify-content-between align-items-center">
                                    <h6 class="mb-1" style="font-weight: bold; font-size: 14px;">${opp.name}</h6>
                                    <span class="badge" style="background-color: var(--${status_color}-100); color: var(--${status_color}-600);">${opp.status}</span>
                                </div>
                                <div class="d-flex w-100 justify-content-between align-items-center mt-2">
                                    <small class="text-muted"><i class="fa fa-calendar text-muted mr-1"></i> ${date}</small>
                                    <small style="font-weight: 500; font-size: 13px; color: var(--text-color);"><i class="fa fa-user-circle-o text-muted mr-1"></i> Assigned To: <b>${assigned_person}</b></small>
                                </div>
                            </a>
                        `;
                    });
                    html += '</div>';
                    d.set_df_property('history_html', 'options', html);
                } else {
                    d.set_df_property('history_html', 'options', `
                        <div class="text-center text-muted" style="padding: 40px; background: var(--bg-light); border-radius: 8px;">
                            <i class="fa fa-folder-open-o mb-3" style="font-size: 32px;"></i>
                            <h6 style="margin-bottom: 0;">No previous opportunities found.</h6>
                        </div>
                    `);
                }
            }
        });
    });

    // We also need to map the get_item to handle the structured object correctly
    awesomplete.get_item = function(value) {
        for(let i=0; i<this._list.length; i++) {
            if(this._list[i].value === value) return this._list[i];
        }
        return null;
    };


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
        let notes = $('#notes').val();

        if (!first_name || !mobile || !assign_to) {
            frappe.msgprint(__("Name, Mobile Number, and Assigned To are mandatory."));
            return;
        }

        let formatted_mobile = mobile.replace(/\D/g, '');
        if (formatted_mobile.length === 10) {
            formatted_mobile = '91' + formatted_mobile;
        }
        let wa_link = `https://wa.me/${formatted_mobile}`;

        btn.prop('disabled', true).text(__('Creating...'));

        if (existing_customer_id) {
            // SCENARIO B: Existing Customer -> Direct to Opportunity
            frappe.call({
                method: "frappe.client.insert",
                args: {
                    doc: {
                        doctype: "Opportunity",
                        opportunity_from: "Customer",
                        party_name: existing_customer_id,
                        contact_mobile: mobile,
                        custom_assigned_to: assign_to,
                        custom_wa_chat_link: wa_link,
                        notes: notes
                    }
                },
                callback: function (res) {
                    btn.prop('disabled', false).text(__('Add New'));
                    if (res.message) {
                        let opp_name = res.message.name;
                        
                        frappe.show_alert({message: __('Opportunity created for existing Customer!'), indicator: 'green'});

                        frappe.call({
                            method: "frappe.desk.form.assign_to.add",
                            args: {
                                assign_to: [assign_to],
                                doctype: "Opportunity",
                                name: opp_name,
                                description: "Auto-Assigned from Quick Entry"
                            }
                        });

                        $('#whatsapp_link').attr('href', wa_link);
                        $('#whatsapp_container').show();
                    }
                }
            });
        } else {
            // SCENARIO A: New Target -> Lead then Opportunity
            frappe.call({
                method: "frappe.client.insert",
                args: {
                    doc: {
                        doctype: "Lead",
                        first_name: first_name,
                        mobile_no: mobile,
                        status: "Open",
                        custom_assigned_to: assign_to,
                        custom_wa_chat_link: wa_link,
                        notes: notes
                    }
                },
                callback: function (r) {
                    if (r.message) {
                        let lead_name = r.message.name;

                        frappe.call({
                            method: "frappe.desk.form.assign_to.add",
                            args: {
                                assign_to: [assign_to],
                                doctype: "Lead",
                                name: lead_name,
                                description: "Auto-Assigned from Quick Entry"
                            }
                        });

                        frappe.call({
                            method: "erpnext.crm.doctype.lead.lead.make_opportunity",
                            args: {
                                source_name: lead_name
                            },
                            callback: function (res) {
                                if (res.message) {
                                    let opportunity_doc = res.message;
                                    opportunity_doc.doctype = "Opportunity";

                                    opportunity_doc.contact_mobile = mobile;
                                    opportunity_doc.custom_assigned_to = assign_to;
                                    opportunity_doc.custom_wa_chat_link = wa_link;
                                    opportunity_doc.notes = notes;

                                    frappe.call({
                                        method: "frappe.client.insert",
                                        args: { doc: opportunity_doc },
                                        callback: function (final_res) {
                                            btn.prop('disabled', false).text(__('Add New'));
                                            if (final_res.message) {
                                                let opp_name = final_res.message.name;
                                                
                                                frappe.show_alert({message: __('Lead and Opportunity created successfully!'), indicator: 'green'});

                                                frappe.call({
                                                    method: "frappe.desk.form.assign_to.add",
                                                    args: {
                                                        assign_to: [assign_to],
                                                        doctype: "Opportunity",
                                                        name: opp_name,
                                                        description: "Auto-Assigned from Quick Entry"
                                                    }
                                                });

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
        }
    });


};