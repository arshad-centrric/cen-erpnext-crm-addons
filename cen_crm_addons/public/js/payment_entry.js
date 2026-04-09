frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        set_screenshot_mandatory(frm);

        if (frappe.route_options && frappe.route_options.from_delivery_dashboard) {
            frm.from_delivery_dashboard = true;
            delete frappe.route_options.from_delivery_dashboard;
        }

        if (frm.from_delivery_dashboard) {
            frm.add_custom_button(__('Back to Delivery Dashboard'), function() {
                frappe.set_route('delivery_dashboard');
            });
        }
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
