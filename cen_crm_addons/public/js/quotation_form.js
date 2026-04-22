frappe.ui.form.on("Quotation", {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // View Opportunity Link
            if (frm.doc.opportunity) {
                let btn = frm.add_custom_button(__('View Opportunity'), function() {
                    frappe.set_route('Form', 'Opportunity', frm.doc.opportunity).then(() => {
                        cur_frm.reload_doc();
                    });
                });
                btn.removeClass('btn-default').css({
                    'background-color': '#000',
                    'color': '#fff',
                    'border-color': '#000'
                });
            }

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

            // Request Revision Flow (Section 1 & 2)
            const add_revision_dialog = (label) => {
                frm.add_custom_button(label, function() {
                    let d = new frappe.ui.Dialog({
                        title: __('Revision Details'),
                        fields: [
                            {
                                label: __('Reason for Revision'),
                                fieldname: 'reason',
                                fieldtype: 'Small Text',
                                default: frm.doc.custom_revision_reason || '',
                                reqd: 1
                            }
                        ],
                        primary_action_label: __('Submit'),
                        primary_action(values) {
                            frappe.call({
                                method: 'cen_crm_addons.api.opportunity_automation.request_quotation_revision',
                                args: {
                                    quotation: frm.doc.name,
                                    reason: values.reason
                                },
                                freeze: true,
                                callback: function(r) {
                                    if (!r.exc) {
                                        d.hide();
                                        frappe.show_alert({
                                            message: __('Revision reason updated and Opportunity status changed.'),
                                            indicator: 'green'
                                        });
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    });
                    d.show();
                });
            };

            // Rule 1: Always show 'View Revise Reason' if reason exists (even if canceled)
            if (frm.doc.custom_revision_reason) {
                add_revision_dialog(__('View Revise Reason'));
            } 
            // Rule 2: Show 'Request Revision' only if Submitted and Opportunity is NOT Delivered/Closed
            else if (frm.doc.docstatus === 1 && frm.doc.opportunity) {
                frappe.db.get_value("Opportunity", frm.doc.opportunity, "status", (r) => {
                    if (r && r.status && !["Delivered", "Closed"].includes(r.status)) {
                        add_revision_dialog(__('Request Revision'));
                    }
                });
            }
        }
    }
});

