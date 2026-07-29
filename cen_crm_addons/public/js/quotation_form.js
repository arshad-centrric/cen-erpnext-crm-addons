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

            // Phase 2: Split Delivery Wizard Logic
            if (frm.doc.docstatus === 1) {
                setTimeout(() => {
                    frm.remove_custom_button('Sales Order', 'Create');
                    frm.add_custom_button(__('Sales Order'), function() {
                        frm.reload_doc().then(() => {
                            let locations = frm.doc.custom_location_details || [];
                    
                    if (locations.length === 0) {
                        // Standard flow
                        frappe.model.open_mapped_doc({
                            method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
                            frm: frm
                        });
                    } else if (locations.length === 1) {
                        // Single Address Bypass - automatically select the only address and all pending items
                        let allocate_items = [];
                        let has_pending = false;
                        
                        (frm.doc.items || []).forEach((item) => {
                            let ordered_qty = item.ordered_qty || 0;
                            let pending_qty = item.qty - ordered_qty;
                            
                            if (pending_qty > 0) {
                                allocate_items.push({
                                    item_code: item.item_code,
                                    quotation_item_name: item.name,
                                    allocate_qty: pending_qty
                                });
                                has_pending = true;
                            }
                        });
                        
                        if (!has_pending) {
                            frappe.msgprint(__('All items have already been ordered.'));
                            return;
                        }
                        
                        frappe.model.open_mapped_doc({
                            method: "cen_crm_addons.api.sales_order_hooks.make_split_sales_order",
                            frm: frm,
                            args: {
                                source_name: frm.doc.name,
                                payload: {
                                    target_address_row_name: locations[0].name,
                                    items: allocate_items
                                }
                            }
                        });
                    } else {
                        // Split Delivery Wizard Dialog
                        let address_options = locations.map(row => ({
                            label: row.delivery_label || row.name,
                            value: row.name
                        }));
                        
                        let items_html = `
                            <table class="table table-bordered">
                                <thead>
                                    <tr>
                                        <th>Item Code</th>
                                        <th>Item Name</th>
                                        <th>Total Qty</th>
                                        <th>Pending Qty</th>
                                        <th>Allocate Qty</th>
                                    </tr>
                                </thead>
                                <tbody>
                        `;
                        
                        let has_pending = false;
                        
                        (frm.doc.items || []).forEach((item, idx) => {
                            let ordered_qty = item.ordered_qty || 0;
                            let pending_qty = item.qty - ordered_qty;
                            
                            items_html += `
                                <tr data-item-code="${item.item_code}" data-name="${item.name}" data-pending="${pending_qty}">
                                    <td>${item.item_code}</td>
                                    <td>${item.item_name}</td>
                                    <td>${item.qty}</td>
                                    <td>${pending_qty}</td>
                                    <td>
                                        <input type="number" class="form-control allocate-qty-input" data-idx="${idx}" max="${pending_qty}" min="0" value="0" ${pending_qty <= 0 ? 'disabled' : ''}>
                                    </td>
                                </tr>
                            `;
                            
                            if (pending_qty > 0) has_pending = true;
                        });
                        
                        items_html += `
                                </tbody>
                            </table>
                        `;
                        
                        if (!has_pending) {
                            frappe.msgprint(__('All items have already been ordered.'));
                            return;
                        }

                        let d = new frappe.ui.Dialog({
                            title: __('Split Delivery Allocation'),
                            fields: [
                                {
                                    label: __('Select Target Address'),
                                    fieldname: 'selected_address',
                                    fieldtype: 'Select',
                                    options: address_options,
                                    reqd: 1
                                },
                                {
                                    fieldname: 'items_html',
                                    fieldtype: 'HTML',
                                    options: items_html
                                }
                            ],
                            primary_action_label: __('Create Sales Order'),
                            primary_action(values) {
                                let allocate_items = [];
                                let has_error = false;
                                let total_allocated_qty = 0;
                                let total_pending_qty = 0;
                                
                                d.$wrapper.find('.allocate-qty-input').each(function() {
                                    let qty = parseFloat($(this).val()) || 0;
                                    let max = parseFloat($(this).attr('max')) || 0;
                                    let item_name = $(this).closest('tr').attr('data-name');
                                    let item_code = $(this).closest('tr').attr('data-item-code');
                                    
                                    total_pending_qty += max;
                                    
                                    if (qty > max) {
                                        frappe.msgprint(__('Cannot allocate more than Pending Qty for item {0}', [item_code]));
                                        has_error = true;
                                        return false;
                                    }
                                    
                                    if (qty > 0) {
                                        total_allocated_qty += qty;
                                        allocate_items.push({
                                            item_code: item_code,
                                            quotation_item_name: item_name,
                                            allocate_qty: qty
                                        });
                                    }
                                });
                                
                                if (has_error) return;
                                
                                if (allocate_items.length === 0) {
                                    frappe.msgprint(__('Please allocate at least 1 item.'));
                                    return;
                                }
                                
                                d.get_primary_btn().prop('disabled', true);
                                
                                frappe.call({
                                    method: 'cen_crm_addons.api.sales_order_hooks.get_linked_sales_orders',
                                    args: {
                                        quotation_name: frm.doc.name
                                    },
                                    callback: function(r) {
                                        let sales_orders = r.message || [];
                                        let fulfilled_locations_count = sales_orders.length;
                                        let total_locations = frm.doc.custom_location_details ? frm.doc.custom_location_details.length : 0;
                                        let unfulfilled_locations = total_locations - fulfilled_locations_count;
                                        let remaining_items_after_allocation = total_pending_qty - total_allocated_qty;
                                        
                                        if (unfulfilled_locations > 1) {
                                            let required_buffer = unfulfilled_locations - 1;
                                            if (remaining_items_after_allocation < required_buffer) {
                                                frappe.msgprint(__('Cannot allocate all items. You must leave at least {0} item(s) pending for the remaining {1} delivery location(s).', [required_buffer, required_buffer]));
                                                d.get_primary_btn().prop('disabled', false);
                                                return;
                                            }
                                        }
                                        
                                        frappe.model.open_mapped_doc({
                                            method: "cen_crm_addons.api.sales_order_hooks.make_split_sales_order",
                                            frm: frm,
                                            args: {
                                                source_name: frm.doc.name,
                                                payload: {
                                                    target_address_row_name: values.selected_address,
                                                    items: allocate_items
                                                }
                                            }
                                        });
                                        
                                        d.hide();
                                    }
                                });
                            }
                        });
                        
                        d.show();
                    }
                        });
                }, __('Create'));
                
                    // Polish Create Button Group
                    let create_btn = frm.page.wrapper.find('.page-actions button:contains("Create")').filter(function() {
                        return $(this).text().trim() === "Create" || $(this).text().trim() === __("Create");
                    }).first();
                    
                    if (create_btn.length === 0) {
                        create_btn = frm.page.wrapper.find('.page-actions button:contains("Create")').first();
                    }
                    
                    if (create_btn.length > 0) {
                        create_btn.removeClass('btn-default').css({
                            'background-color': '#000',
                            'color': '#fff',
                            'border-color': '#000'
                        });
                        
                        let view_opp_btn = frm.page.wrapper.find('.page-actions button:contains("View Opportunity")');
                        if (view_opp_btn.length > 0) {
                            create_btn.closest('.custom-btn-group, .btn-group').insertAfter(view_opp_btn);
                        }
                    }
                }, 100);
            }
            // Custom Update Items Flow
            if (frm.doc.docstatus === 1 && !['Lost', 'Ordered', 'Cancelled'].includes(frm.doc.status)) {
                frappe.dom.set_style('.btn[data-label="Update%20Items"] { display: none !important; }');
                
                frm.add_custom_button(__('Update Items and Rate'), function() {
                    let initial_data = (frm.doc.items || []).map(row => {
                        return {
                            docname: row.name,
                            item_code: row.item_code,
                            item_name: row.item_name,
                            qty: row.qty,
                            rate: row.rate,
                            amount: (row.qty || 0) * (row.rate || 0),
                            name: row.name
                        };
                    });

                    let d = new frappe.ui.Dialog({
                        title: __('Update Items'),
                        size: 'extra-large',
                        fields: [
                            {
                                fieldname: 'items',
                                fieldtype: 'Table',
                                label: __('Items'),
                                data: initial_data,
                                get_data: () => { return initial_data; },
                                fields: [
                                    { fieldname: 'docname', fieldtype: 'Data', hidden: 1 },
                                    { 
                                        fieldname: 'item_code', 
                                        fieldtype: 'Link', 
                                        options: 'Item', 
                                        in_list_view: 1, 
                                        label: __('Item Code'), 
                                        read_only: 0, 
                                        only_select: 1, 
                                        formatter: (value) => value,
                                        change: function() {
                                            const me = this;
                                            if (!me.value) return;
                                            me.doc.qty = 1;
                                            frappe.call({
                                                method: 'erpnext.stock.get_item_details.get_item_details',
                                                args: {
                                                    doc: frm.doc,
                                                    ctx: {
                                                        item_code: me.value,
                                                        company: frm.doc.company,
                                                        price_list: frm.doc.selling_price_list,
                                                        currency: frm.doc.currency,
                                                        doctype: frm.doc.doctype,
                                                        name: frm.doc.name,
                                                        customer: frm.doc.customer || frm.doc.party_name,
                                                        qty: 1
                                                    }
                                                },
                                                callback: function(r) {
                                                    if (r && r.message) {
                                                        me.doc.item_name = r.message.item_name;
                                                        me.doc.rate = flt(r.message.price_list_rate) || flt(r.message.rate) || 0.0;
                                                        me.doc.amount = flt(me.doc.qty) * flt(me.doc.rate);
                                                        d.fields_dict.items.grid.refresh();
                                                    }
                                                }
                                            });
                                        }
                                    },
                                    { fieldname: 'item_name', fieldtype: 'Data', in_list_view: 1, label: __('Item Name'), read_only: 1 },
                                    { 
                                        fieldname: 'qty', 
                                        fieldtype: 'Float', 
                                        in_list_view: 1, 
                                        label: __('Qty'),
                                        change: function() {
                                            this.doc.amount = flt(this.doc.qty) * flt(this.doc.rate);
                                            d.fields_dict.items.grid.refresh();
                                        }
                                    },
                                    { 
                                        fieldname: 'rate', 
                                        fieldtype: 'Currency', 
                                        in_list_view: 1, 
                                        label: __('Rate'),
                                        change: function() {
                                            this.doc.amount = flt(this.doc.qty) * flt(this.doc.rate);
                                            d.fields_dict.items.grid.refresh();
                                        }
                                    },
                                    { fieldname: 'amount', fieldtype: 'Currency', in_list_view: 1, label: __('Amount'), read_only: 1 }
                                ]
                            }
                        ],
                        primary_action_label: __('Update'),
                        primary_action: function(values) {
                            let updated_items = values.items || [];
                            let trans_items = updated_items.filter(u => !!u.item_code).map(u => {
                                return {
                                    docname: u.docname || null,
                                    item_code: u.item_code,
                                    qty: u.qty,
                                    rate: u.rate
                                };
                            });

                            frappe.call({
                                method: 'erpnext.controllers.accounts_controller.update_child_qty_rate',
                                freeze: true,
                                args: {
                                    parent_doctype: frm.doc.doctype,
                                    parent_doctype_name: frm.doc.name,
                                    child_docname: 'items',
                                    trans_items: trans_items
                                },
                                callback: function(r) {
                                    if (!r.exc) {
                                        d.hide();
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    });
                    


                    d.show();
                });
            }
        }
    }
});

