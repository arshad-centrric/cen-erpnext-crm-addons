frappe.listview_settings['Sales Order'] = {
    onload(listview) {
        // Add Custom Button to the header
        let btn = listview.page.add_inner_button(__('View Opportunity List'), function() {
            frappe.set_route('List', 'Opportunity');
        });

        // Style the button black
        btn.css({
            'background-color': '#000',
            'color': '#fff',
            'border-color': '#000'
        }).removeClass('btn-default');

        // Add Keyboard Shortcut: Shift + O
        frappe.ui.keys.add_shortcut({
            shortcut: 'shift+o',
            action: () => frappe.set_route('List', 'Opportunity'),
            description: __('Go to Opportunity List'),
            page: listview.page
        });
    }
};
