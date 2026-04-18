app_name = "cen_crm_addons"
app_title = "Cen Crm Addons"
app_publisher = "Centrric Innovations PVT LTD"
app_description = "App related to CRM requirements"
app_email = "support@centrric.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cen_crm_addons",
# 		"logo": "/assets/cen_crm_addons/logo.png",
# 		"title": "Cen Crm Addons",
# 		"route": "/cen_crm_addons",
# 		"has_permission": "cen_crm_addons.api.permission.has_app_permission"
# 	}
# ]

fixtures = [
    "Role Profile", 
    "Role", 
    "Custom DocPerm",
    {"dt": "Property Setter", "filters": [["doc_type", "in", ("Opportunity", "Lead", "Opportunity Item", "Item", "Payment Entry", "Sales Order", "Quotation", "Sales Order Item", "Quotation Item", "Opportunity Item")]]},
    {"dt": "Custom Field", "filters": [["fieldname", "in", (
        "custom_assigned_to", 
        "custom_assigned_full_name",
        "custom_wa_chat_link", 
        "custom_delivery_detail", # Section Break
        "custom_delivery_info", # Column Break 1
        "custom_customer_address", # Column Break 2
        "custom_general",
        "custom_address",
        "custom_delivery_store",
        "custom_mode_of_delivery", 
        "custom_delivery_partner", 
        "custom_delivery_date", 
        "custom_delivery_time",
        "custom_address_line_1",
        "custom_address_line_2",
        "custom_delivery_city",
        "custom_delivery_state",
        "custom_pincode",
        "custom_delivery_country",
        "custom_remarks",

        #Opportunity Item
        "custom_view_bundle",
        "custom_is_bundle",

        #Item 
        "custom_crm_details_tab",
        "custom_is_product_bundle",
        # Product Bundle Custom Fields
        "custom_customization_details", # Section Break
        "custom_is_customized_bundle",
        "custom_original_bundle_item",

        # Delivery & Payment
        "custom_payment_status",
        "custom_picking_status",
        "custom_packing_image",
        "custom_payment_screenshot",

        # Opportunity Tabs
        "custom_quotation_tab",
        "custom_quotation_html",
        "custom_sales_order_tab",
        "custom_sales_order_html",

        #Quotation
        "custom_revision_reason"
    )]]}
]






# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cen_crm_addons",
# 		"logo": "/assets/cen_crm_addons/logo.png",
# 		"title": "Cen Crm Addons",
# 		"route": "/cen_crm_addons",
# 		"has_permission": "cen_crm_addons.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/cen_crm_addons/css/jquery-clockpicker.min.css"
app_include_js = [
    "/assets/cen_crm_addons/js/jquery-clockpicker.min.js",
    "/assets/cen_crm_addons/js/time_patch.js"
]

# include js, css files in header of web template
# web_include_css = "/assets/cen_crm_addons/css/cen_crm_addons.css"
# web_include_js = "/assets/cen_crm_addons/js/cen_crm_addons.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cen_crm_addons/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

doctype_js = {
    "Opportunity": "public/js/opportunity.js",
    "Item": "public/js/item.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Quotation": "public/js/quotation_form.js",
    "Sales Order": "public/js/sales_order_form.js"
}
doctype_list_js = {
	"Lead": "public/js/crm_list_formatters.js",
	"Opportunity": "public/js/crm_list_formatters.js",
	"Quotation": "public/js/quotation_list.js",
	"Sales Order": "public/js/sales_order_list.js"
}

# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cen_crm_addons/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cen_crm_addons.utils.jinja_methods",
# 	"filters": "cen_crm_addons.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cen_crm_addons.install.before_install"
# after_install = "cen_crm_addons.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "cen_crm_addons.uninstall.before_uninstall"
# after_uninstall = "cen_crm_addons.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cen_crm_addons.utils.before_app_install"
# after_app_install = "cen_crm_addons.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cen_crm_addons.utils.before_app_uninstall"
# after_app_uninstall = "cen_crm_addons.utils.after_app_uninstall"

after_migrate = [
    "cen_crm_addons.api.naming_series_setup.setup_customer_naming",
    "cen_crm_addons.api.docperm_setup.setup_custom_permissions",
    "cen_crm_addons.api.module_profile_setup.setup_module_profiles",
    "cen_crm_addons.api.picking_setup_utils.setup_picking_profile",
    "cen_crm_addons.api.opportunity_setup.setup_opportunity_statuses"
]

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cen_crm_addons.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Lead": "cen_crm_addons.api.crm_permissions.lead_query",
	"Opportunity": "cen_crm_addons.api.crm_permissions.opportunity_query",
	"Prospect": "cen_crm_addons.api.crm_permissions.prospect_query",
	"Item": "cen_crm_addons.api.crm_permissions.item_query"
}

has_permission = {
	"Lead": "cen_crm_addons.api.crm_permissions.lead_has_permission",
	"Opportunity": "cen_crm_addons.api.crm_permissions.opportunity_has_permission",
	"Prospect": "cen_crm_addons.api.crm_permissions.prospect_has_permission"
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "User Payment Mapping": {
        "on_update": "cen_crm_addons.api.payment_restriction_setup.sync_user_permissions",
        "on_trash": "cen_crm_addons.api.payment_restriction_setup.remove_user_permissions"
    },
    "Lead": {
        "on_update": "cen_crm_addons.api.crm_permissions.sync_lead_list_fields"
    },
    "Opportunity": {
        "on_update": "cen_crm_addons.api.crm_permissions.sync_opportunity_list_fields",
        "after_insert": "cen_crm_addons.api.opportunity_automation.ensure_opportunity_assignment"
    },
    "Product Bundle": {
        "on_update": "cen_crm_addons.api.crm_bundle.sync_parent_is_bundle"
    },
    "Sales Order": {
        "on_update": [
            "cen_crm_addons.api.payment_logic.on_sales_order_update",
            "cen_crm_addons.api.opportunity_automation.on_sales_order_update"
        ],
        "on_update_after_submit": [
            "cen_crm_addons.api.opportunity_automation.on_sales_order_update"
        ]
    },
    "Payment Entry": {
        "validate": "cen_crm_addons.api.payment_logic.validate_payment_screenshot",
        "on_submit": [
            "cen_crm_addons.api.payment_logic.on_payment_entry_update",
            "cen_crm_addons.api.opportunity_automation.on_payment_entry_submit"
        ],
        "on_cancel": "cen_crm_addons.api.payment_logic.on_payment_entry_update"
    },
    "Delivery Note": {
        "on_submit": [
            "cen_crm_addons.api.payment_logic.on_delivery_note_update",
            "cen_crm_addons.api.opportunity_automation.on_delivery_note_submit"
        ],
        "on_cancel": "cen_crm_addons.api.payment_logic.on_delivery_note_update"
    }
}


# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cen_crm_addons.tasks.all"
# 	],
# 	"daily": [
# 		"cen_crm_addons.tasks.daily"
# 	],
# 	"hourly": [
# 		"cen_crm_addons.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cen_crm_addons.tasks.weekly"
# 	],
# 	"monthly": [
# 		"cen_crm_addons.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "cen_crm_addons.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
    "erpnext.crm.doctype.opportunity.opportunity.make_quotation": "cen_crm_addons.api.sales_order_hooks.make_quotation_wrapper",
    "erpnext.selling.doctype.quotation.quotation.make_sales_order": "cen_crm_addons.api.sales_order_hooks.make_sales_order_wrapper"
}

#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cen_crm_addons.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cen_crm_addons.utils.before_request"]
# after_request = ["cen_crm_addons.utils.after_request"]

# Job Events
# ----------
# before_job = ["cen_crm_addons.utils.before_job"]
# after_job = ["cen_crm_addons.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cen_crm_addons.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

