# Box ID Generation Architecture (Store-Wise)

## Overview
Initially, the Box ID was generated using global flat fields in the `Cen CRM Settings` doctype. As operations expanded to multiple companies and physical locations, this was migrated to a relational Store-wise (Parent Warehouse) architecture using a Child Table.

## Data Structure (Phase 1)
**Parent Doctype:** `Cen CRM Settings`
**Child Doctype:** `Box ID Configuration Item`
*   `parent_warehouse` (Link: Warehouse) - The store generating the Box ID.
*   `box_id_prefix` (Data) - e.g., AGT, CCJ.
*   `current_box_id_number` (Int) - The rolling counter.

## API Logic (Phase 2 - Complete)
The backend logic now dynamically resolves the strictly allowed Warehouse from `User Permission` rules during Opportunity creation. It then securely maps this to the `store_box_id_configurations` child table in `Cen CRM Settings` to generate a localized Box ID series.

* **File:** `cen_crm_addons/api/opportunity_hooks.py`
* **Function:** `generate_box_id`
