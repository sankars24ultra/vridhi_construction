# 5. Reports and Financial Calculations

[Documentation home](README.md)

## How Export report works

1. Open the permitted module and confirm the project.
2. Set the relevant filters and inspect the rows.
3. Select Export report and wait while data/fonts are prepared.
4. The browser opens its print dialog.
5. Choose **Save as PDF** (or the OS PDF destination), choose all required pages,
   and inspect the preview. Landscape can help wide tables.
6. Save the file to your chosen location.

This is browser printing, not automatic server-side PDF generation. Browser
paper size, scaling, margins and header/footer settings affect the output.
Cancel closes the dialog without saving; a recorded export event can still exist.

Print styles use white backgrounds and dark text even when Dark mode is enabled.
Sidebar, top controls and personal Notes are excluded. The shared report header
includes company name/logo, report title/date and project context where available.
Its address is currently the literal placeholder **Company Address**; replace
that implementation value before distributing official external reports.

## Export scope is module-specific

| Module | Current implemented data preparation |
|---|---|
| Overview | Prints its loaded dashboard; restricted Procurement/Cash flow sections remain empty |
| Procurement | Fetches all project POs before print; its export fetch does not carry the on-screen search/payment filter |
| Inventory | Prints the current rendered register and summaries; check material/search filters and visible pagination |
| Cash flow | Prints rendered billing and receipt sections; check each register's current filter/page |
| Labor and Wages | Prints rendered labor sections; expand relevant sections and check section pagination |
| Users | Loads the directory through all API pages; prints currently search-filtered directory rows |
| Audit Log | Fetches every page matching project, search and applied time interval; expands change details for print |

Do not assume every PDF includes every database row simply because Audit Log
and Procurement explicitly fetch full datasets. For modules that print rendered
pages, verify preview coverage; use larger page sizes or separate exports as
needed. This document describes current behavior, not a new export-scope fix.

Plan/contract Download icons retrieve original uploaded files; they are not
report exports. The Audit API also retains a CSV option for technical clients,
but the current Audit Log UI's Export report uses print/Save as PDF.

## Understand the Overview numbers

| Figure | Current basis | Do not confuse with |
|---|---|---|
| Contract value | Project contract values/current estimate | Client cash already collected |
| Materials cost | PO line quantity x unit price, summed | Remaining stock value or only paid purchases |
| Direct labor cost | Recorded work quantity x rate | Wage payments |
| Contract labor cost | Certified progress-claim amounts | All draft claims or contract payments |
| Actual cost | Materials ordered + direct work earnings + certified labor claims | Cash leaving the bank |
| Open commitments | Outstanding PO balances | All future subcontract exposure |
| Invoiced/billed amount | Recorded billing-entry amounts | Full contract value |
| Cash received | All recorded client receipts | Only allocated receipts |
| Billed outstanding | Billed amount less receipts allocated to applications, bounded at zero | Contract value minus all cash received |
| Projected margin | (Contract value - actual cost) / contract value x 100 | Final audited profit |

The zero-contract case is handled separately by the application rather than
dividing by zero. Monthly costs use the current purchasing/work/claim records;
they are not a general-ledger cash statement. Equipment/other categories must
not be assumed populated merely because the dashboard exposes them.

### Worked example (illustrative, not live data)

- PO value: INR 100,000; vendor payments: INR 30,000.
- Direct work earnings: INR 10,000; certified contract claims: INR 20,000.
- Contract value: INR 200,000.
- Actual cost: INR 130,000; procurement outstanding: INR 70,000.
- Projected margin: 35%, not the amount of available cash.
- Billed: INR 80,000; client receipts: INR 50,000, of which INR 40,000 allocated.
- Billed outstanding: INR 40,000; cash received remains INR 50,000.

## Reconciliation checklist

1. Compare the same project, currency, record states and date basis.
2. Procurement total ordered should reconcile to material PO cost.
3. Procurement paid + outstanding should reconcile to ordered value.
4. Inventory available stock is physical/valuation data, not the PO cost total.
5. Direct earnings plus certified labor claims should reconcile to labor cost.
6. Cash receipts and billed applications should reconcile to their underlying rows.
7. Do not subtract a payment twice from earned/certified cost.
8. Inspect incomplete allocation, unapproved claims and filtered/paginated rows
   before concluding that totals are wrong.

## Audit interpretation

Audit timestamps are stored with timezone information and displayed in browser
local time. The UI converts the selected interval into timezone-aware parameters.
To includes the selected ending minute. Newest-first ordering uses timestamp
and audit ID as a tie-breaker.

Record is the entity type; Reference is its internal ID, not necessarily a
human-readable PO number. View changes describes recorded differences. Older
events can lack full snapshots. Visit logging begins with the implemented
tracking mechanism and cannot reconstruct historical browsing.

Export activity describes a request, never a verified downloaded or saved file.
