frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        set_screenshot_mandatory(frm);
    },
    mode_of_payment: function(frm) {
        set_screenshot_mandatory(frm);
    }
});

function set_screenshot_mandatory(frm) {
    if (frm.doc.payment_type === "Receive") {
        // Mandatory if not Cash
        let is_mandatory = (frm.doc.mode_of_payment && frm.doc.mode_of_payment !== "Cash") ? 1 : 0;
        frm.toggle_reqd('custom_payment_screenshot', is_mandatory);
    }
}
