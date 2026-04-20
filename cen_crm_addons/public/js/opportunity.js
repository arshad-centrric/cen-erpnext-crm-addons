frappe.ui.form.on('Opportunity Item', {
    item_code: function (frm, cdt, cdn) {
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
    custom_view_bundle: function (frm, cdt, cdn) {
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
            filters: { 'new_item_code': item_code },
            fields: ['name']
        },
        callback: function (r) {
            if (r.message && r.message.length > 0) {
                let bundle_name = r.message[0].name;

                // Stage 2: Fetch the full parent and child tables for the exact bundle
                frappe.call({
                    method: 'frappe.client.get',
                    args: { doctype: 'Product Bundle', name: bundle_name },
                    callback: function (res) {
                        if (res.message && res.message.items) {
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
        primary_action: function () {
            d.hide();
        },
        secondary_action_label: __('Customize Bundle'),
        secondary_action: function () {
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
        $(wrapper).find('.bundle-qty-input').on('change', function () {
            let i = $(this).attr('data-idx');
            customized_items[i].qty = parseFloat($(this).val()) || 1;
        });

        $(wrapper).find('.bundle-remove-btn').on('click', function () {
            let i = $(this).attr('data-idx');
            customized_items.splice(i, 1);
            render_table(wrapper); // Re-render
        });

        $(wrapper).find('.bundle-reset-btn').on('click', function () {
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

        $(wrapper).find('.bundle-back-btn').on('click', function () {
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
                click: function () {
                    let new_code = d.get_value('new_item_code');
                    let new_qty = d.get_value('new_item_qty');
                    if (new_code && new_qty > 0) {
                        // Check if exists
                        let exists = customized_items.find(i => i.item_code === new_code);
                        if (exists) {
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
        primary_action: function () {
            if (customized_items.length === 0) {
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
                callback: function (r) {
                    if (r.message) {
                        let new_bundle_item_code = r.message;
                        // Successfully customized, update opportunity line
                        frappe.model.set_value(cdt, cdn, 'item_code', new_bundle_item_code).then(() => {
                            frappe.show_alert({ message: __('Bundle Customized Successfully'), indicator: 'green' });
                            d.hide();
                        });
                    }
                },
                always: function () {
                    d.get_primary_btn().prop('disabled', false);
                }
            });
        }
    });

    // Initial Render
    render_table(d.fields_dict.bundle_table_html.wrapper);
    d.show();
}

frappe.ui.form.on('Opportunity', {
    refresh: function (frm) {
        // Start by hiding the tabs. They will be revealed if data exists.
        frm.set_df_property('custom_quotation_tab', 'hidden', 1);
        frm.set_df_property('custom_sales_order_tab', 'hidden', 1);

        // Add WhatsApp Chat Redirection Button
        if (frm.doc.custom_wa_chat_link) {
            setTimeout(() => {
                if (frm.page.wrapper.find('.wa-chat-icon').length === 0) {
                    let btn = $(`<button class="btn btn-default wa-chat-icon" title="Chat on WhatsApp" style="background: transparent; border: none; box-shadow: none; padding: 4px 8px; margin-right: 5px;">
                        <i class="fa fa-whatsapp" style="color: #25D366; font-size: 26px;"></i>
                    </button>`).on('click', function() {
                        window.open(frm.doc.custom_wa_chat_link, '_blank');
                    });
                    
                    // prepend to the page actions header so it sits next to other icons
                    frm.page.wrapper.find('.page-actions').prepend(btn);
                }
            }, 200);
        }

        if (!frm.is_new()) {
            frappe.call({
                method: "cen_crm_addons.api.opportunity_details.get_linked_documents",
                args: { opportunity_name: frm.doc.name },
                callback: function (r) {
                    if (r.message) {
                        let data = r.message;

                        // Handle Quotations
                        if (data.quotations && data.quotations.length > 0) {
                            frm.set_df_property('custom_quotation_tab', 'hidden', 0);
                            let q_html = cen_crm_generate_docs_html(data.quotations, 'quotation');
                            frm.set_df_property('custom_quotation_html', 'options', q_html);
                        }

                        // Handle Sales Orders
                        if (data.sales_orders && data.sales_orders.length > 0) {
                            frm.set_df_property('custom_sales_order_tab', 'hidden', 0);
                            let so_html = cen_crm_generate_docs_html(data.sales_orders, 'sales order');
                            frm.set_df_property('custom_sales_order_html', 'options', so_html);
                        }
                    }
                }
            });

            // Set Status Header Buttons (Dropdown)
            if (!frm.doc.__islocal) {
                const statuses = ["Replied", "To be quoted", "Quotation Sent"];
                
                statuses.forEach(status => {
                    frm.page.add_inner_button(__(status), () => {
                        frm.set_value('status', status);
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: __(`Status updated to {0}`, [status]),
                                indicator: 'green'
                            });
                        });
                    }, __('Set Status'));
                });

                // Smart Quotation Flow
                // Remove all predefined inner options to "empty out" the Create button 
                // without destroying the parent, preventing Frappe from re-rendering them.
                setTimeout(() => {
                    frm.page.remove_inner_button('Quotation', 'Create');
                    frm.page.remove_inner_button('Supplier Quotation', 'Create');
                    frm.page.remove_inner_button('Request For Quotation', 'Create');
                    frm.page.remove_inner_button('Customer', 'Create');
                }, 200);


                frappe.db.get_list('Quotation', {
                    filters: {
                        opportunity: frm.doc.name,
                        docstatus: ['in', [0, 1]]
                    },
                    fields: ['name'],
                    limit: 1
                }).then(records => {
                    if (records && records.length > 0) {
                        // Active Quotation exists
                        let active_quotation = records[0].name;
                        frm.add_custom_button(__('View Active Quotation'), () => {
                            frappe.set_route('Form', 'Quotation', active_quotation);
                        });
                    } else {
                        // No active Quotation, allow creation
                        let btn = frm.add_custom_button(__('Create Quotation'), () => {
                            frappe.model.open_mapped_doc({
                                method: 'erpnext.crm.doctype.opportunity.opportunity.make_quotation',
                                frm: frm
                            });
                        });

                        // Apply primary style for emphasis
                        btn.removeClass('btn-default').addClass('btn-primary');
                    }
                });
            }
        }
    }
});






function cen_crm_generate_docs_html(docs, doctype_label) {
    let ht = `<div class="row" style="margin-top: 10px; padding: 10px;">`;
    docs.forEach(doc => {
        let status_class = "secondary";
        let s = (doc.status || "").toLowerCase();

        if (s.includes('open') || s.includes('draft')) status_class = "orange";
        else if (s.includes('submit') || s.includes('paid')) status_class = "green";
        else if (s.includes('cancel')) status_class = "red";
        else status_class = "blue";

        let link_doctype_url_part = doctype_label === 'quotation' ? 'quotation' : 'sales-order';
        let display_date = doc.transaction_date ? frappe.datetime.str_to_user(doc.transaction_date).split(' ')[0] : 'No Date';

        let badges_html = '';
        if (doctype_label === 'quotation') {
            badges_html = `<span class="badge" style="background-color: var(--${status_class}-100); color: var(--${status_class}-600);">${doc.status || 'Unknown'}</span>`;
        } else {
            // Sales Order Specific Statuses
            let picking = doc.custom_picking_status || "Pending";
            let payment = doc.custom_payment_status || "Unpaid";
            let delivery = doc.delivery_status || "Not Delivered";

            let pick_color = "gray";
            let p_lower = picking.toLowerCase();
            if (p_lower.includes("completed") || p_lower.includes("packed")) pick_color = "green";
            else if (p_lower.includes("pending")) pick_color = "orange";
            else if (p_lower.includes("progress")) pick_color = "blue";

            let pay_color = "gray";
            let pay_lower = payment.toLowerCase();
            if (pay_lower === "paid") pay_color = "green";
            else if (pay_lower.includes("unpaid") || pay_lower.includes("pending")) pay_color = "orange";
            else if (pay_lower.includes("partially")) pay_color = "yellow";

            let del_color = "gray";
            let d_lower = delivery.toLowerCase();
            if (d_lower === "delivered") del_color = "green";
            else if (d_lower.includes("not delivered") || d_lower.includes("pending")) del_color = "orange";
            else if (d_lower.includes("partially")) del_color = "yellow";

            badges_html = `
                <div style="display: flex; flex-direction: column; gap: 6px; align-items: flex-end;">
                    <span class="badge" style="background-color: var(--${pick_color}-100); color: var(--${pick_color}-600); width: max-content;">
                        <i class="fa fa-cube text-muted" style="margin-right: 4px;"></i> Picking: ${picking}
                    </span>
                    <span class="badge" style="background-color: var(--${pay_color}-100); color: var(--${pay_color}-600); width: max-content;">
                        <i class="fa fa-credit-card text-muted" style="margin-right: 4px;"></i> Payment: ${payment}
                    </span>
                    <span class="badge" style="background-color: var(--${del_color}-100); color: var(--${del_color}-600); width: max-content;">
                        <i class="fa fa-truck text-muted" style="margin-right: 4px;"></i> Delivery: ${delivery}
                    </span>
                </div>
            `;
        }

        let packing_attachment_html = '';
        if (doctype_label === 'sales order' && doc.custom_packing_image) {
            let filename = doc.custom_packing_image.split('/').pop();
            packing_attachment_html = `
                <div style="margin-top: 15px; border-top: 1px solid var(--gray-200); padding-top: 12px;">
                    <strong style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 8px;">Packing Attachment:</strong>
                    <a href="${doc.custom_packing_image}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; background: var(--gray-100); padding: 6px 10px; border-radius: 4px; border: 1px solid var(--gray-200); color: var(--text-color); text-decoration: none; width: max-content;" onclick="event.stopPropagation();">
                        <i class="fa fa-paperclip text-muted" style="font-size: 13px;"></i> <span style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${filename}</span>
                    </a>
                </div>
            `;
        }

        ht += `
        <div class="col-md-6 mb-3">
            <a href="/app/${link_doctype_url_part}/${doc.name}" class="card border" target="_blank" style="text-decoration: none; color: inherit; padding: 15px; border-radius: 8px; display: block; box-shadow: 0 1px 3px rgba(0,0,0,0.05); transition: 0.2s;">
                <div class="d-flex justify-content-between align-items-start">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <h5 style="margin: 0; font-weight: bold; color: var(--primary); font-size: 15px; display: flex; align-items: center; gap: 8px;">
                            ${doc.name}
                            <button class="btn btn-xs btn-default" style="padding: 2px 6px;" onclick="event.stopPropagation(); event.preventDefault(); window.open('/app/print/${doctype_label === 'quotation' ? 'Quotation' : 'Sales Order'}/${doc.name}', '_blank');" title="Print">
                                <i class="fa fa-print text-muted"></i>
                            </button>
                        </h5>
                        <div class="text-muted" style="font-size: 12px;">
                            <i class="fa fa-calendar" style="width: 14px; text-align: center;"></i> ${display_date}
                        </div>
                        ${(doctype_label === 'quotation' && doc.custom_revision_reason) ? `
                            <div style="margin-top: 5px; line-height: 1.4;">
                                <span style="color: #d9534f; font-size: 11px;">
                                    <b>Revision Reason:</b> ${doc.custom_revision_reason}
                                </span>
                            </div>
                        ` : ''}
                    </div>
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                        ${badges_html}
                        <div style="font-weight: 600; font-size: 15px; color: var(--text-color);">
                            ${format_currency(doc.grand_total, doc.currency)}
                        </div>
                    </div>
                </div>
                ${packing_attachment_html}
            </a>
        </div>`;
    });
    ht += `</div>`;

    // Bottom Section: Payment Details (Only for Sales Orders)
    if (doctype_label === 'sales order') {
        let all_payments = [];
        docs.forEach(doc => {
            if (doc.payment_entries && doc.payment_entries.length > 0) {
                doc.payment_entries.forEach(pe => {
                    pe.so_name = doc.name;
                    pe.so_currency = doc.currency;
                    all_payments.push(pe);
                });
            }
        });

        if (all_payments.length > 0) {
            ht += `<div style="margin-top: 15px; padding: 10px;">
                    <h6 style="color: var(--text-muted); font-weight: bold; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid var(--gray-200); padding-bottom: 8px;">
                        <i class="fa fa-credit-card"></i> Payment Details
                    </h6>
                    <div class="row">`;

            all_payments.forEach(pe => {
                let amount_formatted = format_currency(pe.paid_amount, pe.so_currency);
                let mode = pe.mode_of_payment || 'Unknown Mode';

                let pe_attachments = '';
                if (pe.files && pe.files.length > 0) {
                    pe_attachments += `<div style="margin-top: 12px; padding-top: 8px;">
                        <strong style="font-size: 12px; color: var(--text-muted); display: block; margin-bottom: 8px;">Payment Attachments:</strong>
                        <div style="display: flex; flex-direction: column; gap: 6px;">`;
                    pe.files.forEach(f => {
                        pe_attachments += `<a href="${f.file_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; font-size: 12px; background: var(--gray-100); padding: 6px 10px; border-radius: 4px; border: 1px solid var(--gray-200); color: var(--text-color); text-decoration: none; width: max-content;" onclick="event.stopPropagation();">
                            <i class="fa fa-paperclip text-muted" style="font-size: 13px;"></i> <span style="text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${f.file_name}</span>
                        </a>`;
                    });
                    pe_attachments += `</div></div>`;
                } else {
                    pe_attachments = `<div style="margin-top: 12px; padding: 10px; background: var(--bg-light); border-radius: 6px; border: 1px dashed var(--gray-300); text-align: center; font-size: 12px; color: var(--text-muted);">
                         <i class="fa fa-image text-extra-muted" style="font-size: 18px; margin-bottom: 4px; display: block;"></i> No receipt attached
                     </div>`;
                }

                ht += `<div class="col-md-4 mb-3">
                    <div class="card border" style="padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); background: #ffffff;">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <a href="/app/payment-entry/${pe.name}" target="_blank" style="font-size: 14px; font-weight: bold; color: var(--primary); text-decoration: none;">${pe.name}</a>
                                <span class="badge" style="background-color: var(--blue-100); color: var(--blue-600); font-size: 11px; width: max-content;">${mode}</span>
                            </div>
                            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
                                <a href="/app/sales-order/${pe.so_name}" target="_blank" style="font-size: 13px; font-weight: 600; color: var(--text-muted); text-decoration: none;">${pe.so_name}</a>
                                <strong style="color: var(--green-600); font-size: 15px;">${amount_formatted}</strong>
                            </div>
                        </div>
                        ${pe_attachments}
                    </div>
                </div>`;
            });

            ht += `</div></div>`;
        }
    }

    return ht;
}
