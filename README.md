# Shop Manager

An offline, session-only CustomTkinter desktop prototype based on the first seven supplied mockups.

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

The Products sidebar entry opens a small catalog using the existing product tiles so every product detail is reachable. The final Products screen and Settings await the next mockup batch. Settings currently shows a notification.

The sample cart totals NGN 5,400. `SAVE10` applies a 10% discount that follows the current subtotal. Hold stores one sale for the session; resuming it swaps with the active sale. Cash checkout validates the received amount and calculates change; transfer checkout uses the exact total.

## Data Boundaries

All products, sales, audit entries, edits, held sales, and notes exist only in memory. Restarting restores the sample data. Checkout creates a session sale and corresponding audit entry, preserving item names/prices as snapshots. It does not deduct inventory or write a database. Stock is checked before checkout.

Sample historical records are dated September 2025; Home shows the latest trading day rather than falsely presenting old data as today's transactions. Dashboard and history totals derive from the same records. A new checkout uses the current date.

PDF and printer buttons display explicit prototype notifications. No printer jobs, PDF files, authentication, manager PIN, production stock ledger, SQLite, network service, or cloud synchronization are implemented. CSV export is functional and only writes a file when a destination is selected. Product management edits are session demonstrations, not a production authorization or audit system.

## Structure

```text
main.py                   Entry point
run.bat                   Windows launcher
requirements.txt          Runtime dependencies
ui/app.py                 Root window, sidebar, routing, notifications
ui/theme.py               Palette, typography, currency formatting
ui/components/            Shared widgets, charts, tables, dialogs
ui/pages/                 Home, sale/catalog, history, detail views
services/mock_store.py    Session data and mock cart/checkout operations
assets/products/          Bundled product photos
assets/sources.json       Per-image attribution and source URLs
assets/fetch_products.py  Optional development-only asset downloader
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
```

The native UI smoke test opens the desktop application, traverses the seven screens and catalog, checks the main mock sale workflow, and captures window-only screenshots at 1440x940 and 1180x720. It requires an interactive Windows desktop and briefly brings the app forward for each screenshot. It temporarily uses a fixed display scale for reproducible images; normal application startup respects Windows scaling and fits the available screen. The focused layout check also verifies the product grid at native Windows DPI.

## Image Credits

Product reference photos are from [Supermart.ng](https://www.supermart.ng/), credited to the retailer and respective brands. See `assets/sources.json` for the exact source pages and images. Photos are bundled for this local educational prototype; some pack sizes differ from the mock product labels. No redistribution license is claimed. The optional downloader is never imported by the app; running the app requires no internet connection.
