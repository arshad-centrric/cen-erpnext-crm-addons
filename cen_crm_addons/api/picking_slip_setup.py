import frappe
import json

def execute():
    """
    Creates or updates the Picking Slip Custom Print Format for Sales Order.
    Includes Parent/Child Bundle Logic and condensed table styling.
    """
    print_format_name = "Picking Slip"
    
    html_content = """<style>
    /* Base Typography & Layout */
    .print-format-custom {
        font-family: inherit;
        font-size: 11px;
        color: #000;
    }
    .print-format-custom p, .print-format-custom h3, .print-format-custom h4 {
        margin-top: 0;
    }
    
    /* Header Styles */
    .pf-header {
        margin-bottom: 15px;
        border-bottom: 2px solid #000; 
        padding-bottom: 5px; 
        margin-left: 0; 
        margin-right: 0;
    }
    .company-name {
        margin-bottom: 0px; 
        font-weight: bold;
        font-size: 18px; 
        text-transform: uppercase;
        line-height: 1;
    }
    
    /* Document Title */
    .document-title {
        margin-bottom: 15px;
        font-weight: 900; 
        letter-spacing: 3px; 
        font-size: 20px;
        text-align: center;
        text-transform: uppercase;
    }

    /* Meta Info Box */
    .meta-section {
        margin-bottom: 15px;
        border: 1px solid #000 !important;
        padding: 10px;
        border-radius: 2px;
        overflow: hidden; 
    }
    .meta-label {
        font-size: 13px; 
        font-weight: bold; 
        text-transform: uppercase;
    }
    
    /* QR Code Wrapper */
    .qr-wrapper {
        text-align: right;
    }

    /* Table Styles - CONDENSED */
    .print-format-custom .table {
        margin-bottom: 15px;
        border-collapse: collapse;
        width: 100%;
    }
    .print-format-custom .table td, 
    .print-format-custom .table th {
        padding: 4px 6px; /* Small gaps as requested */
        vertical-align: middle;
        font-size: 11px;
        border: 1px solid #000 !important; 
    }
    .print-format-custom .table th {
        background-color: #f5f5f5 !important; 
        font-weight: bold !important;
        text-transform: uppercase;
        text-align: center;
    }
    
    .item-name {
        font-size: 11px;
        font-weight: bold;
    }
    .item-code {
        font-size: 9px; 
        color: #444;
    }
    
    /* Combo Indicator */
    .combo-badge {
        font-size: 9px; 
        color: #d9534f; 
        border: 1px solid #d9534f; 
        padding: 1px 4px; 
        border-radius: 2px;
        margin-left: 5px;
        vertical-align: middle;
    }

    /* Checkbox for physical picking */
    .checkbox-box {
        width: 16px;
        height: 16px;
        border: 1.5px solid #000;
        margin: 0 auto;
    }
    
    .checkbox-box-child {
        width: 12px;
        height: 12px;
        border: 1px solid #000;
        margin: 0 auto;
    }

    /* The Spacer Hack for wkhtmltopdf */
    .pdf-spacer {
        height: 80px; 
        width: 100%;
        clear: both;
    }

    /* Signatures */
    .signature-section {
        page-break-inside: avoid;
        clear: both; 
    }
    .signature-line {
        border-top: 1px solid #000;
        width: 80%;
        padding-top: 5px;
        font-weight: bold;
        text-align: center;
    }
</style>

<div class="print-format-custom">
    {% set cmp = frappe.get_doc("Company", doc.company) %}
    
    <div class="row pf-header">
        <div class="col-xs-8" style="padding-top: 20px;">
            <h3 class="company-name">{{ cmp.company_name }}</h3>
        </div>
        <div class="col-xs-4 text-right">
            {% if cmp.company_logo %}
               <img src="{{ frappe.utils.get_url(cmp.company_logo) }}" style="max-height: 70px; object-fit: contain;">
            {% endif %}
        </div>
    </div>
    
    <div class="document-title">
        PICKING SLIP
    </div>
    
    <div class="meta-section">
        <div class="col-xs-8" style="padding-left: 0;">
            <div style="margin-bottom: 8px;">
                <span style="color: #333;">Customer:</span><br>
                <span class="meta-label">{{ doc.customer_name }}</span><br>
                <span style="font-size: 10px; color: #444; font-weight: bold;">ID: {{ doc.customer }}</span>
            </div>
            
            <div style="margin-bottom: 8px;">
                <span style="color: #333;">Delivery Store (Source):</span><br>
                <span style="font-size: 13px; font-weight: bold;">{{ doc.set_warehouse or 'N/A' }}</span>
            </div>
            
            <div>
                <span style="color: #333;">Delivery Date:</span><br>
                <span style="font-size: 13px; font-weight: bold;">{{ doc.get_formatted("delivery_date") }}</span>
            </div>
        </div>
        
        <div class="col-xs-4 qr-wrapper" style="padding-right: 0;">
            <div style="color: #333; margin-bottom: 3px; font-size: 10px;">Order ID (Scan):</div>
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{ doc.name | urlencode }}" style="height: 90px; width: 90px; border: 1px solid #000; padding: 2px;" alt="QR Code">
            <div style="font-weight: bold; margin-top: 3px; font-size: 14px;">{{ doc.name }}</div>
        </div>
    </div>
    
    <table class="table">
        <thead>
            <tr>
                <th width="5%">SR</th>
                <th width="65%" style="text-align: left;">ITEM TO PICK</th>
                <th width="15%">QTY</th>
                <th width="15%">PICKED (\u2714)</th>
            </tr>
        </thead>
        <tbody>
            {% for row in doc.items %}
            
                <!-- Find Child Items from packed_items table -->
                {% set child_items = [] %}
                {% if doc.packed_items %}
                    {% for p_item in doc.packed_items %}
                        {% if p_item.parent_detail_docname == row.name %}
                            {% set _ = child_items.append(p_item) %}
                        {% endif %}
                    {% endfor %}
                {% endif %}
                
                <!-- Main Item Row -->
                <tr>
                    <td class="text-center" style="font-weight: bold;">{{ loop.index }}</td>
                    <td>
                        <span class="item-name">{{ row.item_name }}</span>
                        {% if child_items|length > 0 %}
                            <span class="combo-badge">COMBO BUNDLE</span>
                        {% endif %}
                        
                        {% if row.item_code != row.item_name %}
                        <br><span class="item-code">Code: {{ row.item_code }}</span>
                        {% endif %}
                        {% if row.description and row.description != row.item_name %}
                        <br><span style="font-size: 9px; color: #555;">{{ row.description | striptags }}</span>
                        {% endif %}
                    </td>
                    <td class="text-center" style="font-size: 12px; font-weight: bold;">
                        {{ row.qty | round(2) }} <span style="font-size: 9px; font-weight: normal; color: #333;">{{ row.uom }}</span>
                    </td>
                    <td class="text-center">
                        <div class="checkbox-box"></div>
                    </td>
                </tr>
                
                <!-- Child Items Rows (if applicable) -->
                {% if child_items|length > 0 %}
                    {% for c_item in child_items %}
                    <tr style="background-color: #fafbfc;">
                        <td></td> <!-- Empty SR for child items -->
                        <td style="padding-left: 20px;">
                            <span style="color: #888;">&#10551;</span> 
                            <span class="item-name" style="font-size: 10px;">{{ c_item.item_name }}</span>
                            {% if c_item.item_code != c_item.item_name %}
                            &nbsp;<span class="item-code">({{ c_item.item_code }})</span>
                            {% endif %}
                        </td>
                        <td class="text-center" style="font-size: 11px; font-weight: bold;">
                            {{ c_item.qty | round(2) }} <span style="font-size: 8px; font-weight: normal; color: #333;">{{ c_item.uom }}</span>
                        </td>
                        <td class="text-center">
                            <div class="checkbox-box-child"></div>
                        </td>
                    </tr>
                    {% endfor %}
                {% endif %}
                
            {% endfor %}
        </tbody>
    </table>
    
    <div class="pdf-spacer"></div>
    
    <div class="row signature-section">
        <div class="col-xs-6">
            <div class="signature-line">Picked By</div>
        </div>
        <div class="col-xs-6">
            <div class="signature-line" style="float: right;">Date / Time</div>
        </div>
    </div>
</div>"""

    if not frappe.db.exists("Print Format", print_format_name):
        doc = frappe.new_doc("Print Format")
        doc.name = print_format_name
        doc.doc_type = "Sales Order"
        doc.custom_format = 1
        doc.html = html_content
        doc.print_format_type = "Jinja"
        doc.insert(ignore_permissions=True)
    else:
        doc = frappe.get_doc("Print Format", print_format_name)
        doc.html = html_content
        doc.custom_format = 1
        doc.doc_type = "Sales Order"
        doc.print_format_type = "Jinja"
        doc.save(ignore_permissions=True)
    
    frappe.db.commit()
