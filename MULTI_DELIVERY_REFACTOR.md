# Multi-Delivery Refactor: cen_crm_addons

## System Context
Project: ERPNext Custom App (`cen_crm_addons`).
Client Problem: The client handles "Group Buy" or "Split-Shipment" scenarios where a single Lead/Opportunity needs items shipped to multiple different addresses (e.g., buying for friends).
Current Architecture Limitations: The `Opportunity` and `Quotation` DocTypes currently use flat, single-instance custom fields for delivery (e.g., `custom_delivery_store`, `custom_mode_of_delivery`, `custom_delivery_partner`, `custom_delivery_date`, `custom_delivery_time`, `custom_address_line_1`, `custom_address_line_2`, `custom_delivery_city`, `custom_delivery_state`, `custom_pincode`, `custom_delivery_country`). This only supports one address per document.

## The Refactor Plan
We are executing a multi-phase refactor to support 1-to-Many delivery routing.

- **Phase 1**: Convert flat delivery fields into a new Child Table (`Delivery Info Detail`). We will do this Doctype by Doctype, starting strictly with `Opportunity`.
  > **CRITICAL CONSTRAINT:** Production data exists. Old flat fields CANNOT be deleted. They will be hidden, data will be migrated via script to the new Child Table, and only then will old fields be dropped.
- **Phase 2**: Build a custom allocation UI/wizard. When creating a Sales Order from a Quotation, the user will select which items/quantities go to which saved delivery address, generating multiple separate Sales Orders.

## Status
**Phase 1, Task 2 Complete**: 
- Created `Delivery Info Detail` Child Table.
- Added New Section **"Delivery Locations"** in Opportunity.
- Added Table Field **"Location Details"** (`custom_location_details`) linked to the child table.
- Original delivery fields and section (`custom_delivery_detail`) are set to hidden.

**Next Task**: Phase 1, Task 3: Data Migration Script.
