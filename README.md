# Shop Manager

An offline, session-only CustomTkinter desktop prototype based on the first two supplied mockup batches.

## Run

From this folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe main.py
```

Or double-click `run.bat`. Python 3.14 and the required packages are already installed in the local `.venv`.

For a new environment:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Dependencies: CustomTkinter 6.0.0 and Pillow 12.3.0. CustomTkinter also installs its own small dependencies. Windows Segoe UI and Segoe MDL2 Assets supply the typography and icons; a generic icon fallback is available on other platforms.

## This Batch

- Home: summary totals, sales chart, recent sales, low-stock products, quick navigation.
- New Sale: product search, exact barcode/name entry with Enter, category filter, sorting, cart quantity controls, item removal, cart clearing, discount, hold/resume, checkout.
- Sales History: search, date/payment filters, date sorting, pagination, sale details, CSV export.
- Sale Details: item snapshots, payment information, receipt preview, editable session notes.
- Audit Logs: search, date/action/user filters, date sorting, pagination, CSV export.
- Audit Log Details: action information, linked sale, change summary, session notes.
- Product Details: overview, sales chart, sales history, session stock/price history, price/cost/stock forms, product edit form, barcode copying, add-to-sale, delete confirmation.

Products now has a searchable, filterable, paginated table with compact edit, stock, and delete actions. Add/Edit Product supports local PNG/JPG uploads. Adjust Stock records a reason and before/after snapshots. Audit entries open a right-hand detail drawer without losing the underlying filters. Checkout opens a payment review followed by a sale-completed receipt summary. Settings still awaits its mockup batch.

Sensitive product edits, stock adjustments, and deletion use a demonstration manager PIN: `1234`. This is a session-only UI gate, not production authentication. Canceling authorization leaves the data unchanged.

New Sale has independent product and cart scrolling, with totals and checkout pinned below the cart. Cart updates reuse unchanged rows and product tiles. Main pages are cached; document pages are refreshed after data changes. Image thumbnails are cached locally. Native Windows title bars avoid CustomTkinter's hide/show recoloring workaround, which could cause flashing and blank dialogs. The first visit still constructs each page's widgets.

The sample cart totals NGN 5,400. `SAVE10` applies a 10% discount that follows the current subtotal. Hold stores one sale for the session; resuming it swaps with the active sale. Cash checkout validates the received amount and calculates change; transfer checkout uses the exact total.

## Data Boundaries

All products, sales, audit entries, edits, held sales, and notes exist only in memory. Restarting restores the sample data. Checkout creates a session sale and corresponding audit entry, preserving item names/prices as snapshots. It does not deduct inventory or write a database. Stock is checked before checkout.

Sample historical records are dated September 2025; Home shows the latest trading day rather than falsely presenting old data as today's transactions. Dashboard and history totals derive from the same records. A new checkout uses the current date.

PDF and printer buttons display explicit prototype notifications; email is disabled. No printer jobs, PDF files, production authentication, production stock ledger, SQLite, network service, or cloud synchronization are implemented. CSV export is functional and only writes a file when a destination is selected. Uploaded images remain in memory for the session. Product management edits are session demonstrations, not a production authorization or audit system.

## Structure

```text
main.py                   Entry point
run.bat                   Windows launcher
requirements.txt          Runtime dependencies
ui/app.py                 Root window, sidebar, routing, notifications
ui/theme.py               Palette, typography, currency formatting
ui/components/            Shared widgets, charts, tables, dialogs
ui/pages/                 Home, POS, products table, history, detail views
services/mock_store.py    Session data and mock cart/checkout operations
assets/products/          Bundled product photos
assets/sources.json       Per-image attribution and source URLs
data/                     Reserved for later local data
database/                 Reserved for later SQLite code
tests/                    Focused model tests and native desktop smoke test
artifacts/                Local verification screenshots (ignored by Git)
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe tests\ui_smoke.py
.\.venv\Scripts\python.exe tests\layout_check.py
.\.venv\Scripts\python.exe tests\batch_two_smoke.py
```

The native UI smoke test opens the desktop application, traverses the seven screens and catalog, checks the main mock sale workflow, and captures window-only screenshots at 1440x940 and 1180x720. It requires an interactive Windows desktop and briefly brings the app forward for each screenshot. It temporarily uses a fixed display scale for reproducible images; normal application startup respects Windows scaling and fits the available screen. The focused layout check also verifies the product grid at native Windows DPI.

## Image Credits

Product reference photos are credited to Supermart.ng and respective brands. See `assets/sources.json` for provenance metadata only; these URLs are never loaded by the app. Photos are bundled for this local educational prototype; some pack sizes differ from the mock product labels. No redistribution license is claimed. The development downloader has been removed. The batch-two smoke test blocks sockets and DNS while exercising navigation, local image upload, authorization, stock changes, and checkout.
