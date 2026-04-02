frappe.ui.form.on('Opportunity Item', {
    item_code: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        if (row.item_code) {
            // Fetch rate from Item Price automatically based on Standard Selling
            frappe.db.get_value("Item Price", {
                item_code: row.item_code,
                price_list: "Standard Selling"
            }, "price_list_rate").then(r => {
                if (r && r.message && r.message.price_list_rate !== undefined) {
                    frappe.model.set_value(cdt, cdn, "rate", r.message.price_list_rate);
                }
            });
        }
    },
    custom_view_bundle: function(frm, cdt, cdn) {
        let row = frappe.get_doc(cdt, cdn);
        // Ensure it's marked as a bundle either by Checkbox int (1) or string ("1")
        if (row.item_code && (row.custom_is_bundle == 1 || row.custom_is_bundle == true || row.custom_is_bundle == "1")) {
            cen_crm_show_bundle_popup(row.item_code);
        }
    }
});

function cen_crm_show_bundle_popup(item_code) {
    // Stage 1: Safely find the Product Bundle record linked to this Item
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Product Bundle',
            filters: {'new_item_code': item_code},
            fields: ['name']
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let bundle_name = r.message[0].name;
                
                // Stage 2: Fetch the full parent and child tables for the exact bundle
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Product Bundle', name: bundle_name },
                    callback: function(res) {
                        if(res.message && res.message.items) {
                            cen_crm_render_popup(item_code, res.message);
                        }
                    }
                });
            } else {
                frappe.msgprint(__('No standard Product Bundle definitions found for this item.'));
            }
        }
    });
}

function cen_crm_render_popup(item_code, bundle_doc) {
    let items_html = `
        <div style="margin-bottom: 15px;">
            <span class="text-muted">Parent Item:</span> <b>${item_code}</b>
            <p>${bundle_doc.description || ""}</p>
        </div>
        <table class="table table-bordered table-hover">
        <thead>
            <tr style="background-color: var(--scrollbar-track-color);">
                <th style="width: 25%">Item Code</th>
                <th style="width: 55%">Description</th>
                <th style="width: 20%; text-align: right;">Quantity</th>
            </tr>
        </thead>
        <tbody>`;
    
    bundle_doc.items.forEach(d => {
        items_html += `
            <tr>
                <td><b>${d.item_code}</b></td>
                <td class="text-muted">${d.description || ''}</td>
                <td style="text-align: right;"><span class="badge badge-success" style="font-size: 13px;">${d.qty}</span></td>
            </tr>`;
    });
    
    items_html += `</tbody></table>`;

    let d = new frappe.ui.Dialog({
        title: __('Bundle Composition'),
        fields: [
            { fieldname: 'bundle_html', fieldtype: 'HTML', options: items_html }
        ],
        primary_action_label: __('Close'),
        primary_action: function() {
            d.hide();
        }
    });
    
    d.show();
}
