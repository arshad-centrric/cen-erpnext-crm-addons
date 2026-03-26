frappe.listview_settings['Opportunity'] = {
    onload: function(listview) {
        // Ensure all necessary fields are included in the data fetch
        listview.add_fields(['contact_mobile', 'assigned_to_name', 'wa_chat_link', 'id_display', 'title', 'status']);
    },
    formatters: {
        wa_chat_link: function(value, df, doc) {
            // Get the phone number from the synced field or the link itself
            let mobile = doc.contact_mobile || "";
            let link = value || "";
            
            // If no link but we have a mobile, construct it
            if (!link && mobile) {
                let phone = mobile.replace(/\D/g, "");
                if (phone) link = "https://wa.me/" + phone;
            }

            if (link) {
                // Return a beautiful green WhatsApp icon
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

// Fail-safe to ensure formatters are registered correctly even if the object is modified elsewhere
$(document).on('list_view_loaded', function() {
    if (frappe.listview_settings['Opportunity']) {
        if (!frappe.listview_settings['Opportunity'].formatters) {
            frappe.listview_settings['Opportunity'].formatters = {};
        }
        // Force the wa_chat_link formatter if missing or overwritten
        if (!frappe.listview_settings['Opportunity'].formatters.wa_chat_link) {
             frappe.listview_settings['Opportunity'].formatters.wa_chat_link = function(value, df, doc) {
                 let mobile = doc.contact_mobile || "";
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
