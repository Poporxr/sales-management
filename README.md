# Shop Manager (Simple)

An offline point-of-sale desktop app for a small shop. Built with
Python, CustomTkinter for the UI, SQLite for storage, fpdf2 for
receipt PDFs, and Pillow for product photos. Written to be simple enough to explain line by line.

## Run

```bash
pip install -r requirements.txt
python main.py
```

On first launch the app creates `data/shop.db`, fills it with 12
sample products and a few recent sample sales, and creates
`store.json` with default shop details.

## Features

- **Home**: today's sales count and revenue, product count,
  out-of-stock warnings, recent sales.
- **New Sale**: search by name or barcode (Enter on an exact barcode
  adds it like a scanner), category filter, sorting, cart with
  quantity controls, cash/transfer checkout with change calculation.
- **Receipt preview**: after checkout the receipt appears inside the
  app, styled like a thermal slip. **Print** generates the PDF
  (80mm, minimal) and opens it in your PDF viewer. Nothing is saved
  until you click Print.
- **Products**: searchable catalog with photos, add/edit/delete
  (photo picker on the form), stock adjustment with a required
  reason. Edits, deletes, and stock
  changes ask for the manager PIN (`1234`, demo only).
- **Sales History**: table with column headers (Receipt, Date,
  Cashier, Items, Payment, Total), date filter, and search.
  Double-click a row for the detail view with a **Reprint receipt**
  button. Receipts are regenerated from the stored sale data, so old
  purchases can be reprinted any time.
- **Audit Log**: append-only table with column headers (Date, User,
  Action, Details) and a date filter. Records critical actions only
  (product added/edited/deleted, stock adjusted, sale completed).
- **Cashier picker**: choose who is at the till on startup; the name
  is stamped on sales and audit entries.

Checkout deducts stock, validates quantities, and freezes each
item's name and price on the receipt, so later edits never rewrite
history.

## Project structure

```text
main.py              Entry point: python main.py
store.json           Shop name, address, phone (created on first run)
requirements.txt     customtkinter, fpdf2
database.py          SQLite: plain functions, parameterized queries
shop.py              Business rules: validation, PIN, checkout
receipt.py           On-demand thermal-style PDF receipts
config.py            Loads/creates store.json
ui/app.py            Window, sidebar, simple navigation
ui/theme.py          Colors, fonts, Naira formatting
ui/widgets.py        Tiny widget helpers
ui/receipt_view.py   In-app receipt preview dialog
ui/pages/            welcome, home, pos, products, history, audit
tests/test_store.py  Unit tests: python -m unittest discover -s tests
```

## Where data lives

- `data/shop.db` — the SQLite database (products, sales, audit log).
- `store.json` — shop details shown on screen and receipts.
- Receipts are generated on demand into the system temp folder and
  are never stored by the app.

## Notes

- The manager PIN (`1234` in `shop.py`) is a demo gate, not real
  security. A production app would hash per-user PINs.
- Everything runs offline. There is no network code.
