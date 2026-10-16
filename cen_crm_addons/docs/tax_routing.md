# Tax Routing (company-wise Tax Category)

## Problem

Item Tax rows on Items are tied to a Tax Category (e.g. `In-State`). CRM documents never get a
Tax Category: the Customer is auto-created from the Lead with only a name and phone
(`api/sales_order_hooks.py::_apply_customer_auto_creation`), and nothing else sets it. ERPNext
matches the Item Tax Template on an exact Tax Category, so no template matched, `item_tax_rate`
stayed empty and every line was taxed at 0 from the Quotation through to the Sales Invoice.
ERPNext only re-resolves item taxes in the browser when the Tax Category is changed by hand, and
that helper skips rows that have no Item Tax Template yet.

## Behaviour

`api/tax_routing.py::apply_company_tax_routing` runs on `before_validate` of **Quotation**,
**Sales Order** and **Sales Invoice** (drafts only; POS invoices and returns are skipped).

1. Finds the company's route: its row in **Tax Routing Settings**, else the company's default
   Sales Taxes and Charges Template (`is_default`). The Tax Category is the template's own.
2. If the document has no Tax Category, sets it from the route. Skipped when the document already
   has a *different* template (picked by hand or by India Compliance).
3. On a **new** document with no template and no tax rows, sets the route's template and its tax
   rows.
4. For item rows with no Item Tax Template, resolves one from the Tax Category (the same lookup as
   Get Item Details) and sets `item_tax_template`, `item_tax_rate` and the fetched fields.

Nothing already chosen is overwritten. `validate` then recalculates the totals.

### On the open Quotation form

The save hook alone would leave a new Quotation at 0 tax until the first save, so
`public/js/tax_routing.js` fills the open form too. On `refresh`, `company`, `party_name` and item
selection it calls `api/tax_routing.py::get_tax_routing_details` (the same logic, nothing saved),
then sets the Tax Category and each row's Item Tax Template. ERPNext's own row handler loads the
rate and recalculates. It does nothing when the Tax Category is set and every row has a template.

## Setup

**Tax Routing Settings** (System Manager): one row per company, with the Sales Taxes and Charges
Template. The Tax Category is read-only and fetched from the template. Validation: one row per
company; the template must belong to the company, be enabled and have a Tax Category.

A company with no row works through its default template, so a new branch needs no configuration.

## Notes for rollout

- The routed template decides whether the price is tax-inclusive. `...In-state - AGT` and
  `...- AGTC` have 0% rows with *Included in Print Rate* ticked, so 5% items stay at the quoted
  price. `...- AGTCGC` and `...- AGTK` ship with 9% + 9% *excluded*, so the tax is added on top.
  Align them before relying on this for those companies.
- A company whose Items have no Item Tax rows (currently Kanhangad) still falls back to the
  template's own rate. Item Tax rows must exist for each company to get per-item rates.
- Item Tax rows are tied to `In-State`, so out-of-state sales need `Out-State` rows as well.
- Existing documents are not changed; a draft picks the fix up the next time it is saved.
- Run `bench migrate` on deploy (new doctypes) and `bench clear-cache` (new `doc_events`).
