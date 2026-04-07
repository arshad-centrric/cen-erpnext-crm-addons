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
            cen_crm_show_bundle_popup(row.item_code, frm, cdt, cdn);
        }
    }
});

function cen_crm_show_bundle_popup(item_code, frm, cdt, cdn) {
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
                            cen_crm_render_read_only_popup(item_code, res.message, frm, cdt, cdn);
                        }
                    }
                });
            } else {
                frappe.msgprint(__('No standard Product Bundle definitions found for this item.'));
            }
        }
    });
}

function cen_crm_render_read_only_popup(parent_item_code, bundle_doc, frm, cdt, cdn) {
    let items_html = `
        <div style="margin-bottom: 15px;">
            <span class="text-muted">Parent Item:</span> <b>${parent_item_code}</b>
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
        },
        secondary_action_label: __('Customize Bundle'),
        secondary_action: function() {
            d.hide();
            // Launch the advanced editor
            cen_crm_render_popup(parent_item_code, bundle_doc, frm, cdt, cdn);
        }
    });
    
    d.show();
}

function cen_crm_render_popup(parent_item_code, bundle_doc, frm, cdt, cdn) {
    // 1. Maintain a local array of items to edit
    let customized_items = [];
    bundle_doc.items.forEach(d => {
        customized_items.push({
            item_code: d.item_code,
            qty: d.qty,
            description: d.description || ''
        });
    });

    // 2. Function to re-render the HTML table inside the dialog
    function render_table(wrapper) {
        let html = `
            <style>
                /* Remove browser number spinners */
                input.bundle-qty-input::-webkit-outer-spin-button,
                input.bundle-qty-input::-webkit-inner-spin-button {
                    -webkit-appearance: none;
                    margin: 0;
                }
                input.bundle-qty-input {
                    -moz-appearance: textfield;
                }
            </style>
            <div style="margin-bottom: 15px; display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span class="text-muted">Parent Item:</span> <b>${parent_item_code}</b>
                    <p style="margin-bottom: 5px;">Modify quantities, remove items, or add new ones below.</p>
                </div>
                <div>
                    <button class="btn btn-default btn-xs bundle-back-btn" style="margin-right: 5px;">← Back View</button>
                    <button class="btn btn-default btn-xs bundle-reset-btn">↺ Reset Flow</button>
                </div>
            </div>
            <table class="table table-bordered table-hover">
            <thead>
                <tr style="background-color: var(--scrollbar-track-color);">
                    <th style="width: 35%">Item Code</th>
                    <th style="width: 40%">Description</th>
                    <th style="width: 15%; text-align: right;">Quantity</th>
                    <th style="width: 10%; text-align: center;">Act</th>
                </tr>
            </thead>
            <tbody>`;
        
        customized_items.forEach((d, idx) => {
            html += `
                <tr>
                    <td><b>${d.item_code}</b></td>
                    <td class="text-muted" style="font-size: 11px;">${d.description}</td>
                    <td style="text-align: right;">
                        <input type="number" class="form-control form-control-sm bundle-qty-input" data-idx="${idx}" value="${d.qty}" min="0" step="any" style="text-align: right;">
                    </td>
                    <td style="text-align: center;">
                        <button class="btn btn-xs btn-danger bundle-remove-btn" data-idx="${idx}">X</button>
                    </td>
                </tr>`;
        });
        html += `</tbody></table>`;
        
        $(wrapper).html(html);

        // Attach events
        $(wrapper).find('.bundle-qty-input').on('change', function() {
            let i = $(this).attr('data-idx');
            customized_items[i].qty = parseFloat($(this).val()) || 1;
        });
        
        $(wrapper).find('.bundle-remove-btn').on('click', function() {
            let i = $(this).attr('data-idx');
            customized_items.splice(i, 1);
            render_table(wrapper); // Re-render
        });
        
        $(wrapper).find('.bundle-reset-btn').on('click', function() {
            // Restore from original bundle_doc
            customized_items = [];
            bundle_doc.items.forEach(d => {
                customized_items.push({
                    item_code: d.item_code,
                    qty: d.qty,
                    description: d.description || ''
                });
            });
            render_table(wrapper); // Re-render
        });

        $(wrapper).find('.bundle-back-btn').on('click', function() {
            d.hide(); // Hide current dialog
            cen_crm_render_read_only_popup(parent_item_code, bundle_doc, frm, cdt, cdn); // Re-open read only
        });
    }

    // 3. Create Dialog
    let d = new frappe.ui.Dialog({
        title: __('Customize Bundle'),
        size: 'large',
        fields: [
            { fieldname: 'bundle_table_html', fieldtype: 'HTML' },
            { fieldtype: 'Section Break', label: 'Add New Item' },
            { fieldname: 'new_item_code', fieldtype: 'Link', options: 'Item', label: 'Item', in_list_view: 1 },
            { fieldname: 'new_item_qty', fieldtype: 'Float', label: 'Qty', default: 1.0, in_list_view: 1 },
            { fieldtype: 'Column Break' },
            { 
                fieldname: 'add_item_btn', fieldtype: 'Button', label: 'Add to Bundle', 
                click: function() {
                    let new_code = d.get_value('new_item_code');
                    let new_qty = d.get_value('new_item_qty');
                    if(new_code && new_qty > 0) {
                        // Check if exists
                        let exists = customized_items.find(i => i.item_code === new_code);
                        if(exists) {
                            exists.qty += flt(new_qty);
                        } else {
                            // Fetch description
                            d.get_primary_btn().prop('disabled', true);
                            frappe.db.get_value("Item", new_code, "description").then(r => {
                                customized_items.push({
                                    item_code: new_code,
                                    qty: new_qty,
                                    description: (r.message && r.message.description) ? r.message.description : ''
                                });
                                render_table(d.fields_dict.bundle_table_html.wrapper);
                                d.set_value('new_item_code', '');
                                d.set_value('new_item_qty', 1);
                                d.get_primary_btn().prop('disabled', false);
                            });
                            return; // Wait for promise
                        }
                        render_table(d.fields_dict.bundle_table_html.wrapper);
                        d.set_value('new_item_code', '');
                        d.set_value('new_item_qty', 1);
                    }
                }
            }
        ],
        primary_action_label: __('Apply Customizations'),
        primary_action: function() {
            if(customized_items.length === 0) {
                frappe.msgprint("Bundle cannot be empty.");
                return;
            }
            
            d.get_primary_btn().prop('disabled', true);
            
            // Call Backend
            frappe.call({
                method: 'cen_crm_addons.api.crm_bundle.create_customized_bundle',
                args: {
                    parent_item_code: parent_item_code,
                    new_items_json: JSON.stringify(customized_items)
                },
                callback: function(r) {
                    if(r.message) {
                        let new_bundle_item_code = r.message;
                        // Successfully customized, update opportunity line
                        frappe.model.set_value(cdt, cdn, 'item_code', new_bundle_item_code).then(() => {
                            frappe.show_alert({message: __('Bundle Customized Successfully'), indicator: 'green'});
                            d.hide();
                        });
                    }
                },
                always: function() {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });
    
    // Initial Render
    render_table(d.fields_dict.bundle_table_html.wrapper);
    d.show();
}
