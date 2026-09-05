frappe.ui.form.on('Customer', {
    setup: function(frm) {
        frm.set_query("custom_default_receiving_warehouse", function() {
            return {
                filters: {
                    "company": frm.doc.represents_company,
                    "is_group": 0
                }
            };
        });
    }
});
