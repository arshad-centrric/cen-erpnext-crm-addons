frappe.listview_settings['Lead'] = {
    formatters: {
        custom_wa_chat_link: function (val, df, doc) {
            if (val) {
                return `<a href="${val}" target="_blank" onclick="event.stopPropagation();" style="color: #25D366; font-size: 1.4em; padding-left: 5px;" title="${__('Chat on WhatsApp')}">
                            <i class="fa fa-whatsapp"></i>
                        </a>`;
            }
            return "";
        }
    }
};


frappe.listview_settings['Opportunity'] = {
    // 1. Your existing WhatsApp link formatter
    formatters: {
        custom_wa_chat_link: function (val, df, doc) {
            if (val) {
                return `<a href="${val}" target="_blank" onclick="event.stopPropagation();" style="color: #25D366; font-size: 1.4em; padding-left: 5px;" title="${__('Chat on WhatsApp')}">
                            <i class="fa fa-whatsapp"></i>
                        </a>`;
            }
            return "";
        }
    },

    // 2. The Stateful Dialog-Based Date Filter
    onload: function(listview) {
        let date_filter_dialog;

        listview.page.add_inner_button(__('Filter by Date'), function() {
            
            if (!date_filter_dialog) {
                date_filter_dialog = new frappe.ui.Dialog({
                    title: __('Select Date Range'),
                    fields: [
                        {
                            label: __('Date Range'),
                            fieldname: 'date_range',
                            fieldtype: 'DateRange',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Apply Filter'),
                    primary_action: function(values) {
                        let dates = values.date_range;

                        listview.filter_area.remove('transaction_date');

                        if (dates && dates.length === 2) {
                            let from_date = dates[0];
                            let to_date = dates[1];
                            listview.filter_area.add('Opportunity', 'transaction_date', 'Between', [from_date, to_date]);
                        }

                        listview.refresh();
                        date_filter_dialog.hide();
                    }
                });

                // Clear button logic
                date_filter_dialog.set_secondary_action_label(__('Clear Filter'));
                date_filter_dialog.set_secondary_action(function() {
                    date_filter_dialog.set_value('date_range', '');
                    
                    let date_field = date_filter_dialog.get_field('date_range');
                    if (date_field && date_field.datepicker) {
                        date_field.datepicker.clear();
                    }
                    
                    listview.filter_area.remove('transaction_date');
                    
                    listview.refresh();
                    date_filter_dialog.hide();
                });
            }

            // --- THE SAFE SYNCHRONIZATION LOGIC ---
            try {
                // Get the current active list view filters
                let current_filters = listview.filter_area.get();
                
                // Check if 'transaction_date' is among the active filters
                let filter_still_active = current_filters.some(f => f[1] === 'transaction_date');

                // If it is gone (cleared globally), wipe the popup's memory
                if (!filter_still_active) {
                    date_filter_dialog.set_value('date_range', '');
                    let date_field = date_filter_dialog.get_field('date_range');
                    if (date_field && date_field.datepicker) {
                        date_field.datepicker.clear();
                    }
                }
            } catch (e) {
                // If the filter check fails for any reason, quietly ignore it
                // so it doesn't break the popup from opening!
                console.warn("Date filter sync skipped.", e);
            }
            // --------------------------------------

            // Show the popup
            date_filter_dialog.show();
        });
    }
};

// frappe.listview_settings['Opportunity'] = {
//     formatters: {
//         custom_wa_chat_link: function (val, df, doc) {
//             if (val) {
//                 return `<a href="${val}" target="_blank" onclick="event.stopPropagation();" style="color: #25D366; font-size: 1.4em; padding-left: 5px;" title="${__('Chat on WhatsApp')}">
//                             <i class="fa fa-whatsapp"></i>
//                         </a>`;
//             }
//             return "";
//         }
//     }
// };
