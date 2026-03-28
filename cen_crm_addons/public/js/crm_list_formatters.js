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
