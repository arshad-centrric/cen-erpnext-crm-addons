frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        set_screenshot_mandatory(frm);

        // Auto-fetch Box ID when created from standard Sales Order / Invoice button
        if (!frm.doc.custom_box_id && frm.doc.references && frm.doc.references.length > 0) {
            let first_ref = frm.doc.references[0];
            if (first_ref.reference_doctype === 'Sales Order' || first_ref.reference_doctype === 'Sales Invoice') {
                frappe.db.get_value(first_ref.reference_doctype, first_ref.reference_name, 'custom_box_id')
                    .then(r => {
                        if (r.message && r.message.custom_box_id) {
                            frm.set_value('custom_box_id', r.message.custom_box_id);
                        }
                    });
            }
        }

        if (frappe.route_options && frappe.route_options.from_delivery_dashboard) {
            frm.from_delivery_dashboard = true;
            delete frappe.route_options.from_delivery_dashboard;
        }

        if (frm.from_delivery_dashboard) {
            frm.add_custom_button(__('Back to Delivery Dashboard'), function() {
                frappe.set_route('delivery_dashboard');
            });
        }

        if (!frm.is_new()) {
            // View Opportunity Link
            frappe.call({
                method: 'cen_crm_addons.api.opportunity_details.get_opportunity_for_doc',
                args: { doctype: frm.doc.doctype, docname: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        let btn = frm.add_custom_button(__('View Opportunity'), function() {
                            frappe.set_route('Form', 'Opportunity', r.message).then(() => {
                                cur_frm.reload_doc();
                            });
                        });
                        btn.removeClass('btn-default').css({
                            'background-color': '#000',
                            'color': '#fff',
                            'border-color': '#000'
                        });
                    }
                }
            });

            // WhatsApp Icon Injection
            frappe.call({
                method: 'cen_crm_addons.api.opportunity_details.get_wa_link_for_doc',
                args: { doctype: frm.doc.doctype, docname: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        let wa_link = r.message;
                        setTimeout(() => {
                            if (frm.page.wrapper.find('.wa-chat-icon').length === 0) {
                                let btn = $(`<button class="btn btn-default wa-chat-icon" title="Chat on WhatsApp" style="background: transparent; border: none; box-shadow: none; padding: 4px 8px; margin-right: 5px;">
                                    <i class="fa fa-whatsapp" style="color: #25D366; font-size: 26px;"></i>
                                </button>`).on('click', function() {
                                    window.open(wa_link, '_blank');
                                });
                                frm.page.wrapper.find('.page-actions').prepend(btn);
                            }
                        }, 200);
                    }
                }
            });
        }
    },
    mode_of_payment: function(frm) {
        set_screenshot_mandatory(frm);
    },
    before_save: function(frm) {
        if (frm._doc_before_save && frm._doc_before_save.custom_payment_screenshot && !frm.doc.custom_payment_screenshot) {
            frappe.call({
                method: "frappe.client.get_list",
                args: {
                    doctype: "File",
                    filters: {
                        file_url: frm._doc_before_save.custom_payment_screenshot,
                        attached_to_doctype: "Payment Entry",
                        attached_to_name: frm.doc.name
                    }
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        frappe.call({
                            method: "frappe.client.delete",
                            args: {
                                doctype: "File",
                                name: r.message[0].name
                            }
                        });
                    }
                }
            });
        }
    }
});

function set_screenshot_mandatory(frm) {
    if (frm.doc.payment_type === "Receive") {
        // Mandatory if not Cash
        let is_mandatory = (frm.doc.mode_of_payment && frm.doc.mode_of_payment !== "Cash") ? 1 : 0;
        frm.toggle_reqd('custom_payment_screenshot', is_mandatory);
    }
}
