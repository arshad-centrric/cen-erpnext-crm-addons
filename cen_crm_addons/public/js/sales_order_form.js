frappe.ui.form.on("Sales Order", {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // View Opportunity Link
            frappe.call({
                method: 'cen_crm_addons.api.opportunity_details.get_opportunity_for_doc',
                args: { doctype: frm.doc.doctype, docname: frm.doc.name },
                callback: function(r) {
                    if (r.message) {
                        let btn = frm.add_custom_button(__('View Opportunity'), function() {
                            frappe.set_route('Form', 'Opportunity', r.message);
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

            // Assign Packing Automation (Smart Button)
            if (frm.doc.docstatus === 1 && (!frm.doc.custom_picking_status || frm.doc.custom_picking_status === "Pending")) {
                let btn = frm.add_custom_button(__('Assign Packing'), () => {
                    frappe.db.get_single_value('Cen CRM Settings', 'default_picking_slip_format').then(print_format => {
                        if (!print_format) {
                            frappe.msgprint({
                                title: __('Missing Setup'),
                                indicator: 'red',
                                message: __('Please set the <b>Default Picking Slip Format</b> in <a href="/app/cen-crm-settings" target="_blank">Cen CRM Settings</a> before assign packing.')
                            });
                            return;
                        }

                        // Update Status via Server API (to avoid 'In Words' save error on submitted docs)
                        frappe.call({
                            method: 'cen_crm_addons.api.opportunity_automation.update_sales_order_status',
                            args: {
                                sales_order: frm.doc.name,
                                status: 'Assigned to Pack'
                            },
                            freeze: true,
                            callback: function(r) {
                                if (r.message && r.message.status === "success") {
                                    frm.reload_doc().then(() => {
                                        frappe.show_alert({
                                            message: __('Status updated to Assigned to Pack. Opening Print View...'),
                                            indicator: 'green'
                                        });
                                        
                                        // Set route options to pass print format cleanly
                                        frappe.route_options = { "print_format": print_format };
                                        frappe.set_route('print', 'Sales Order', frm.doc.name);
                                    });
                                }
                            }
                        });
                    });
                });

                btn.removeClass('btn-default').css({
                    'background-color': '#000',
                    'color': '#fff',
                    'border-color': '#000'
                });
            }
        }
    }
});

