# Feature History: Custom Update Items Dialog (Quotation)

## Overview
This document tracks the implementation of a fully custom "Adjust Items & Amount" dialog injected into the `Quotation` DocType via `quotation_form.js`. It ensures upgrade safety and resolves backend "Cannot Update After Submit" errors encountered during item revisions.

## Modifications Made

### 1. Core Button Interception & Hiding
- **File Modifed:** `cen_crm_addons/public/js/quotation_form.js`
- **Action:** Injected a CSS style (`frappe.dom.set_style`) during the `refresh` event (when `docstatus === 1`) to permanently hide the native ERPNext "Update Items" button, preventing dual-rendering conflicts.
- **Result:** Native button is securely hidden via `display: none !important;`.

### 2. Custom Dialog Construction
- **Action:** Created a custom button named **"Adjust Items & Amount"** to prevent listener collisions with ERPNext's core JS.
- **UI Element:** Instantiated a `frappe.ui.Dialog` containing a `Table` field.
- **Fields Added:** `item_code` (Data, Read-Only), `qty` (Float), `rate` (Currency), and `amount` (Currency, Read-Only).

### 3. Dynamic Amount Calculation
- **Action:** Hooked a jQuery `.on('change')` event listener directly to the Dialog's grid wrapper (`d.$wrapper`).
- **Logic:** Whenever `qty` or `rate` is adjusted, the script iterates over the grid's internal data (`d.fields_dict.items.grid.data`), performs the math (`flt(qty) * flt(rate)`), updates the row object, and forcefully calls `.refresh()` on the grid to repaint the UI immediately.

### 4. Upgrade-Safe Backend Sync (Primary Action)
- **Problem Resolved:** Calling `frm.save()` directly from the frontend on a submitted Quotation triggered standard validation and threw a "Cannot Update After Submit" error.
- **Solution:** Re-wired the `primary_action` to construct a specific JSON payload (`trans_items` array containing `docname`, `item_code`, `qty`, `rate`) mimicking standard ERPNext behavior.
- **Backend API:** Used `frappe.call()` targeting `erpnext.controllers.accounts_controller.update_child_qty_rate`. This native endpoint safely updates the item rows, recalculates taxes and totals, and saves the document natively on the backend.
- **Callback:** Upon success, `d.hide()` and `frm.reload_doc()` are executed to refresh the view smoothly.

## Next Steps / Notes for Home System
If you are resuming work on this feature:
- Review the `trans_items` payload inside `quotation_form.js` if further fields (like UOM, Conversion Factors) need to be supported by the dialog in the future.
- Test the "Adjust Items & Amount" dialog fully on a submitted Quotation to ensure tax totals recalculate smoothly in edge cases.
