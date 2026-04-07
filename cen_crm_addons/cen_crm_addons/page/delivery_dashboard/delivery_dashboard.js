frappe.pages['delivery_dashboard'].on_page_load = function(wrapper) {
    
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Delivery Dashboard',
        single_column: true
    });

    // 1. Render the HTML Template (Trying two common naming conventions)
    try {
        let template_name = "delivery_dashboard";
        $(frappe.render_template(template_name, {})).appendTo(page.main);
    } catch (e) {
        console.error("Dashboard Template Error:", e);
        // Fallback: If template fails, try to show a simple message
        page.main.html(`<div style="padding: 20px;">
            <h3>Dashboard Loading...</h3>
            <p>If you see this, the JS loaded but the HTML template had an issue. Error: ${e.message}</p>
        </div>`);
    }

    // 2. Initial State & Elements
    let $wrapper = $(wrapper);
    let search_input = $wrapper.find('#order_search');
    let search_btn = $wrapper.find('#btn_search');
    let details_card = $wrapper.find('#order_details_card');
    let empty_state = $wrapper.find('#empty_state');
    
    let current_order = null;

    // 3. Helper: Format Currency
    function format_money(amount, currency) {
        return frappe.format(amount, { fieldtype: 'Currency', currency: currency });
    }

    // 4. Handle URL Parameters (Auto-Load)
    let url_params = frappe.route_options;
    if (url_params && url_params.order_id) {
        search_input.val(url_params.order_id);
        fetch_order_details(url_params.order_id);
    }

    // 5. Search Logic
    search_btn.click(function() {
        let order_id = search_input.val().trim();
        if (order_id) {
            fetch_order_details(order_id);
        }
    });

    search_input.on('keypress', function(e) {
        if (e.which == 13) {
            search_btn.click();
        }
    });

    function fetch_order_details(order_id) {
        search_btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i>');
        
        frappe.call({
            method: "cen_crm_addons.api.delivery_api.get_order_info",
            args: { order_id: order_id },
            callback: function(r) {
                search_btn.prop('disabled', false).html('<i class="fa fa-search"></i>');
                if (r.message && !r.message.error) {
                    render_order_details(r.message);
                } else {
                    frappe.msgprint(__("Sales Order not found or invalid: " + (r.message ? r.message.message : 'Unknown Error')));
                    reset_dashboard();
                }
            }
        });
    }

    function render_order_details(data) {
        current_order = data;
        empty_state.hide();
        details_card.fadeIn();

        // Fill Details
        $wrapper.find('#display_order_id').text(data.name);
        $wrapper.find('#display_customer').text(data.customer_name);
        $wrapper.find('#display_phone').text(data.contact_mobile || data.contact_phone || 'N/A');
        
        let currency = data.currency || 'INR';
        $wrapper.find('#display_total').html(format_money(data.grand_total, currency));
        $wrapper.find('#display_paid').html(format_money(data.advance_paid, currency));
        
        let outstanding = data.grand_total - data.advance_paid;
        $wrapper.find('#display_outstanding').html(format_money(outstanding, currency));

        // Update Badge & Buttons
        let badge = $wrapper.find('#payment_badge');
        let delivery_btn = $wrapper.find('#btn_complete_delivery');
        let payment_btn = $wrapper.find('#btn_collect_payment');
        let msg = $wrapper.find('#delivery_status_msg');

        if (outstanding <= 0) {
            badge.text('PAID').removeClass('badge-danger').addClass('badge-success');
            delivery_btn.prop('disabled', false).removeClass('btn-secondary').addClass('btn-success');
            payment_btn.hide();
            msg.html('Order is fully paid. You may complete the delivery.');
        } else {
            badge.text('UNPAID').removeClass('badge-success').addClass('badge-danger');
            delivery_btn.prop('disabled', true).removeClass('btn-success').addClass('btn-secondary');
            payment_btn.show();
            msg.html(`Balance of ${format_money(outstanding, currency)} must be collected.`);
        }
        
        if (data.delivery_status === 'Fully Delivered') {
            delivery_btn.prop('disabled', true).text('Already Delivered');
            msg.text('This order has already been delivered.');
        }
    }

    // 6. Action: Collect Payment (Deep Server-Side Mapping)
    $wrapper.find('#btn_collect_payment').click(function() {
        if (!current_order) return;
        
        frappe.call({
            method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
            args: {
                dt: "Sales Order",
                dn: current_order.name
            },
            callback: function(r) {
                if (r.message) {
                    var doc = frappe.model.sync(r.message);
                    frappe.set_route("Form", doc[0].doctype, doc[0].name);
                }
            }
        });
    });

    // 7. Action: Complete Delivery
    $wrapper.find('#btn_complete_delivery').click(function() {
        if (!current_order) return;
        
        frappe.confirm(
            `Are you sure you want to complete the delivery for ${current_order.name}? This will create and submit a Delivery Note.`,
            function() {
                frappe.call({
                    method: "cen_crm_addons.api.delivery_api.confirm_delivery",
                    args: { order_id: current_order.name },
                    callback: function(r) {
                        if (r.message && r.message.name) {
                            frappe.show_alert({
                                message: __(`Delivery Note ${r.message.name} created and submitted!`),
                                indicator: 'green'
                            });
                            fetch_order_details(current_order.name);
                        }
                    }
                });
            }
        );
    });

    function reset_dashboard() {
        details_card.hide();
        empty_state.fadeIn();
        search_input.val('');
        current_order = null;
    }
};
