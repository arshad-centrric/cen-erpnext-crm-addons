frappe.ui.form.on("Quotation", {
    refresh: function(frm) {
        if (!frm.is_new()) {
            // View Opportunity Link
            if (frm.doc.opportunity) {
                let btn = frm.add_custom_button(__('View Opportunity'), function() {
                    frappe.set_route('Form', 'Opportunity', frm.doc.opportunity);
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
        }
    }
});
