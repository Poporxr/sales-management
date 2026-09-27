import csv
import math
from datetime import datetime, timedelta
from tkinter import StringVar, filedialog
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import Page, Metric, Table, label, panel, button, entry, select, badge, icon_button


def action_tone(action):
    return {"Sale Completed": "green", "Product Updated": "blue", "Product Added": "amber",
            "Product Deleted": "red", "Settings Changed": "purple", "User Login": "purple"}.get(action, "blue")


class HistoryPage(Page):
    def __init__(self, app, audit=False):
        super().__init__(app)
        self.audit = audit
        self.page_number = 1
        self.ascending = False
        self.query = StringVar()
        self.filtered = []
        header = self.heading("Audit Logs" if audit else "Sales History",
                              "Track all important activities and changes in your store." if audit else "View and manage all sales transactions.")
        button(header, "Export Logs" if audit else "Export", self.export_csv, "export", width=140).pack(side="right")
        filters = panel(self.body)
        filters.pack(fill="x", pady=(0, 16))
        self.dates = select(filters, ["All Dates", "20 Sep - 26 Sep 2025", "Today", "Last 7 Days"], self.refilter, width=205)
        self.dates.pack(side="left", padx=8, pady=8)
        self.search = entry(filters, "Search action, details or user..." if audit else "Search receipt, product or cashier...", self.query)
        self.search.pack(side="left", fill="x", expand=True, padx=8)
        self.filter_one = select(filters, ["All Actions"] + list(dict.fromkeys(x["action"] for x in self.store.logs)) if audit else ["All Payment Methods", "Cash", "Transfer"], self.refilter, width=175)
        self.filter_one.pack(side="left", padx=8)
        self.filter_two = select(filters, ["All Users", "Admin", "Staff 1"] if audit else ["All Statuses", "Completed"], self.refilter, width=135)
        self.filter_two.pack(side="left", padx=8)
        self.metrics = ctk.CTkFrame(self.body, fg_color="transparent")
        self.metrics.pack(fill="x", pady=(0, 16))
        self.table_panel = panel(self.body)
        self.table_panel.pack(fill="both", expand=True)
        self.table_body = ctk.CTkFrame(self.table_panel, fg_color="transparent")
        self.table_body.pack(fill="both", expand=True, padx=14, pady=14)
        self.footer = ctk.CTkFrame(self.table_panel, fg_color="transparent")
        self.footer.pack(fill="x", padx=20, pady=(12, 22))
        self.query.trace_add("write", lambda *_: self.refilter())
        self.refilter()

    def refilter(self, *_):
        query = self.query.get().strip().lower()
        first, second, date_range = self.filter_one.get(), self.filter_two.get(), self.dates.get()
        now = datetime.now()
        source = self.store.logs if self.audit else self.store.sales
        self.filtered = []
        for record in source:
            if date_range == "Today" and record["date"].date() != now.date():
                continue
            if date_range == "Last 7 Days" and record["date"].date() < (now - timedelta(days=6)).date():
                continue
            if date_range == "20 Sep - 26 Sep 2025" and not datetime(2025, 9, 20) <= record["date"] < datetime(2025, 9, 27):
                continue
            if self.audit:
                haystack = f"{record['id']} {record['action']} {record['details']} {record['user']}"
                if first != "All Actions" and first != record["action"]:
                    continue
                if second != "All Users" and second != record["user"]:
                    continue
            else:
                haystack = f"{record['id']} {record['cashier']} " + " ".join(p["name"] + " " + p["barcode"] for p in record["items"])
                if first != "All Payment Methods" and first != record["payment"]:
                    continue
                if second != "All Statuses" and second != record["status"]:
                    continue
            if query in haystack.lower():
                self.filtered.append(record)
        self.filtered.sort(key=lambda r: r["date"], reverse=not self.ascending)
        self.page_number = 1
        self.render_metrics()
        self.render_table()

    def render_metrics(self):
        for child in self.metrics.winfo_children():
            child.destroy()
        if self.audit:
            counts = lambda prefix: sum(r["action"].startswith(prefix) for r in self.filtered)
            values = [("Total Logs", len(self.filtered), "receipt", "blue"),
                      ("Sales", counts("Sale"), "cart", "green"),
                      ("Product Changes", counts("Product"), "box", "purple"),
                      ("System Actions", counts("Settings"), "settings", "amber"),
                      ("Security Events", counts("User"), "shield", "red")]
        else:
            total = sum(s["total"] for s in self.filtered)
            count = len(self.filtered)
            units = sum(p["quantity"] for s in self.filtered for p in s["items"])
            values = [("Total Sales", T.money(total), "chart", "green"),
                      ("Total Transactions", count, "cart", "blue"),
                      ("Total Items Sold", units, "box", "purple"),
                      ("Average Sale", T.money(total / count if count else 0), "money", "amber")]
        for i, (title, value, symbol, tone) in enumerate(values):
            self.metrics.grid_columnconfigure(i, weight=1, uniform="metrics")
            Metric(self.metrics, title, str(value), symbol, tone).grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))

    def render_table(self):
        for child in self.table_body.winfo_children():
            child.destroy()
        for child in self.footer.winfo_children():
            child.destroy()
        if self.audit:
            headings, weights = ["#", "Date & Time", "User", "Action", "Details", "Device"], [2, 4, 2, 4, 8, 2]
        else:
            headings, weights = ["#", "Date & Time", "Items", "Total", "Payment", "Status", "Cashier", "Action"], [2, 4, 2, 3, 3, 3, 2, 2]
        table = Table(self.table_body, headings, weights)
        table.pack(fill="x")
        # The date heading is the sorting control; preserve the same column geometry.
        date_label = table.winfo_children()[0].winfo_children()[1]
        date_label.configure(text="Date & Time " + ("\u2191" if self.ascending else "\u2193"), cursor="hand2")
        date_label.bind("<Button-1>", lambda event: self.toggle_sort())
        start = (self.page_number - 1) * 10
        for record in self.filtered[start:start + 10]:
            go = lambda r=record: self.app.navigate("log", log_id=r["id"]) if self.audit else self.app.navigate("sale", sale_id=r["id"])
            if self.audit:
                values = [record["id"], record["date"].strftime("%d %b %Y, %I:%M %p"), record["user"],
                          lambda p, r=record: badge(p, r["action"], action_tone(r["action"])),
                          lambda p, r=record: label(p, r["details"], 11, color=T.MUTED, wraplength=310), "This Device"]
            else:
                values = [record["id"], record["date"].strftime("%d %b %Y, %I:%M %p"),
                          f"{len(record['items'])} items", T.money(record["total"]),
                          lambda p, r=record: badge(p, r["payment"], "green" if r["payment"] == "Cash" else "blue"),
                          lambda p: badge(p, "Completed"), record["cashier"],
                          lambda p, fn=go: icon_button(p, "eye", fn, "View sale", size=28)]
            table.add(values, go)
        if not self.filtered:
            label(self.table_body, "No matching records", 18, color=T.MUTED).pack(pady=70)
        pages = max(1, math.ceil(len(self.filtered) / 10))
        prev = icon_button(self.footer, "back", lambda: self.move(-1), "Previous page", "neutral")
        prev.pack(side="left", padx=(0, 5))
        prev.configure(state="disabled" if self.page_number == 1 else "normal")
        visible = range(max(1, min(self.page_number - 2, pages - 4)), min(pages, max(5, self.page_number + 2)) + 1)
        for number in visible:
            button(self.footer, str(number), lambda n=number: self.set_page(n),
                   kind="primary" if number == self.page_number else "neutral", width=34).pack(side="left", padx=3)
        nxt = icon_button(self.footer, "next", lambda: self.move(1), "Next page", "neutral")
        nxt.pack(side="left", padx=5)
        nxt.configure(state="disabled" if self.page_number == pages else "normal")
        label(self.footer, f"Showing {start+1 if self.filtered else 0}-{min(start+10, len(self.filtered))} of {len(self.filtered)} {'logs' if self.audit else 'sales'}", 13, color=T.MUTED).pack(side="right")

    def toggle_sort(self):
        self.ascending = not self.ascending
        self.refilter()

    def move(self, delta):
        self.set_page(max(1, min(math.ceil(len(self.filtered) / 10), self.page_number + delta)))

    def set_page(self, number):
        self.page_number = number
        self.render_table()

    def export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.app, title="Export Logs" if self.audit else "Export Sales",
                                          defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                          initialfile="audit-logs.csv" if self.audit else "sales.csv")
        if not path:
            return
        keys = ["id", "date", "user", "action", "details", "result"] if self.audit else ["id", "date", "total", "payment", "status", "cashier"]
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.DictWriter(output, fieldnames=keys)
                writer.writeheader()
                for record in self.filtered:
                    writer.writerow({key: record[key] for key in keys})
            self.app.toast(f"Exported {len(self.filtered)} records.", "success")
        except OSError as error:
            self.app.toast(f"Could not export: {error.strerror}", "error")
