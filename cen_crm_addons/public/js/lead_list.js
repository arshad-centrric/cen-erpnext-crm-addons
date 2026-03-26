frappe.listview_settings['Lead'] = {
    onload: function(listview) {
        // Ensure necessary fields are included in the data fetch
        listview.add_fields(['mobile_no', 'assigned_to_name', 'wa_chat_link', 'name', 'lead_name', 'status']);
    },
    formatters: {
        wa_chat_link: function(value, df, doc) {
            let mobile = doc.mobile_no || "";
            let link = value || "";
            
            if (!link && mobile) {
                let phone = mobile.replace(/\D/g, "");
                if (phone) link = "https://wa.me/" + phone;
            }

            if (link) {
                return `<a href="${link}" target="_blank" title="Chat on WhatsApp" 
                           onclick="event.stopPropagation();" 
                           style="display: inline-block; padding: 4px; color: #25D366; text-decoration: none;">
                    <i class="fa fa-whatsapp" style="font-size: 1.8em; cursor: pointer; vertical-align: middle;"></i>
                </a>`;
            }
            return "";
        },
        assigned_to_name: function(value, df, doc) {
            if (value) {
                return `<span class="text-muted" style="font-weight: 500;">${value}</span>`;
            }
            return '<span class="text-extra-muted">Not Assigned</span>';
        }
    }
};

// Fail-safe
$(document).on('list_view_loaded', function() {
    if (frappe.listview_settings['Lead']) {
        if (!frappe.listview_settings['Lead'].formatters) {
            frappe.listview_settings['Lead'].formatters = {};
        }
        if (!frappe.listview_settings['Lead'].formatters.wa_chat_link) {
             frappe.listview_settings['Lead'].formatters.wa_chat_link = function(value, df, doc) {
                 let mobile = doc.mobile_no || "";
                 let link = value || "";
                 if (!link && mobile) {
                    let phone = mobile.replace(/\D/g, "");
                    if (phone) link = "https://wa.me/" + phone;
                 }
                 if (link) {
                    return `<a href="${link}" target="_blank" onclick="event.stopPropagation();" style="color: #25D366;">
                        <i class="fa fa-whatsapp" style="font-size: 1.8em;"></i>
                    </a>`;
                 }
                 return "";
             };
        }
    }
});
