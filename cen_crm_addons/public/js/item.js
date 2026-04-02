frappe.ui.form.on('Item', {
    refresh: function(frm) {
        cen_crm_toggle_stock_item(frm);
    },
    custom_is_product_bundle: function(frm) {
        if (frm.doc.custom_is_product_bundle) {
            frm.set_value('is_stock_item', 0);
            frappe.show_alert({
                message: __('Maintain Stock is disabled for Product Bundles.'),
                indicator: 'orange'
            });
        }
        cen_crm_toggle_stock_item(frm);
    }
});

function cen_crm_toggle_stock_item(frm) {
    if (frm.doc.custom_is_product_bundle) {
        frm.set_df_property('is_stock_item', 'read_only', 1);
    } else {
        frm.set_df_property('is_stock_item', 'read_only', 0);
    }
}
