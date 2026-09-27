"""Dashboard summaries are derived from the same offline records as history."""

from datetime import datetime
import customtkinter as ctk
from ui import theme as T
from ui.components.widgets import Page, Metric, Chart, label, panel, button, icon, product_image, badge


class HomePage(Page):
    def __init__(self, app):
        super().__init__(app)
        header = self.heading("Welcome Back", "Here's what's happening at your store today.")
        label(header, datetime.now().strftime("%a, %d %b %Y  |  %I:%M %p"), 13,
              color=T.MUTED, image=icon("calendar"), compound="left").pack(side="right")
        # Historical fixtures use a fixed date; show the latest trading day
        # instead of labeling those records as live sales from today.
        latest_date = self.store.sales[0]["date"].date()
        today = [s for s in self.store.sales if s["date"].date() == latest_date]
        low = sorted([p for p in self.store.products if p["stock"] <= p["minimum"]], key=lambda p: p["stock"])
        metrics = ctk.CTkFrame(self.body, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, 18))
        values = [("Latest Day Sales", T.money(sum(s["total"] for s in today)), "money", "green", latest_date.strftime("%d %b %Y")),
                  ("Transactions", str(len(today)), "cart", "blue", "Latest trading day"),
                  ("Units in Stock", str(sum(p["stock"] for p in self.store.products)), "box", "amber", f"{len(self.store.products)} products"),
                  ("Low Stock Items", str(len(low)), "tag", "red", "Needs restocking")]
        for i, value in enumerate(values):
            metrics.grid_columnconfigure(i, weight=1, uniform="metrics")
            Metric(metrics, *value).grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
        columns = ctk.CTkFrame(self.body, fg_color="transparent")
        columns.pack(fill="both", expand=True)
        columns.grid_columnconfigure(0, weight=3, uniform="home")
        columns.grid_columnconfigure(1, weight=2, uniform="home")
        left = ctk.CTkFrame(columns, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        right = ctk.CTkFrame(columns, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        chart_panel = panel(left)
        chart_panel.pack(fill="x", pady=(0, 16))
        chart_head = ctk.CTkFrame(chart_panel, fg_color="transparent")
        chart_head.pack(fill="x", padx=18, pady=(16, 5))
        label(chart_head, "Sales Overview", 18, True).pack(side="left")
        label(chart_head, latest_date.strftime("%d %b"), 12, color=T.MUTED).pack(side="right")
        buckets = [sum(s["total"] for s in today if start <= s["date"].hour < start + 3)
                   for start in [0, 3, 6, 9, 12, 15, 18, 21]]
        Chart(chart_panel, buckets, ["12AM", "3AM", "6AM", "9AM", "12PM", "3PM", "6PM", "9PM"], height=238).pack(fill="x", padx=16, pady=(5, 15))
        stock = panel(left)
        stock.pack(fill="x")
        stock_head = ctk.CTkFrame(stock, fg_color="transparent")
        stock_head.pack(fill="x", padx=18, pady=14)
        label(stock_head, "Low Stock Items", 18, True).pack(side="left")
        button(stock_head, "View All", lambda: app.navigate("products"), "next", width=100).pack(side="right")
        for product in low:
            row = ctk.CTkFrame(stock, fg_color="transparent")
            row.pack(fill="x", padx=18, pady=(0, 9))
            label(row, "", image=product_image(product["image"], 43)).pack(side="left", padx=(0, 14))
            name = ctk.CTkFrame(row, fg_color="transparent")
            name.pack(side="left")
            title = label(name, product["name"], 13, True, cursor="hand2")
            title.pack(anchor="w")
            title.bind("<Button-1>", lambda event, p=product: app.navigate("product", product_id=p["id"]))
            label(name, product["barcode"], 12, color=T.MUTED).pack(anchor="w")
            badge(row, f"{product['stock']} left", "red").pack(side="right")
        recent = panel(right)
        recent.pack(fill="x", pady=(0, 16))
        recent_head = ctk.CTkFrame(recent, fg_color="transparent")
        recent_head.pack(fill="x", padx=18, pady=14)
        label(recent_head, "Recent Sales", 18, True).pack(side="left")
        button(recent_head, "View All", lambda: app.navigate("sales"), "next", width=95).pack(side="right")
        for sale in self.store.sales[:5]:
            row = ctk.CTkFrame(recent, fg_color="transparent", cursor="hand2")
            row.pack(fill="x", padx=18, pady=(0, 12))
            label(row, "", image=icon("receipt", T.MUTED, 23), width=42, height=46,
                  fg_color=T.BG, corner_radius=8).pack(side="left", padx=(0, 12))
            text = ctk.CTkFrame(row, fg_color="transparent")
            text.pack(side="left")
            label(text, f"SALE-{sale['id']}", 13, True).pack(anchor="w")
            label(text, f"{len(sale['items'])} items | {sale['date']:%I:%M %p}", 12, color=T.MUTED).pack(anchor="w")
            label(row, T.money(sale["total"]), 16, True).pack(side="right")
            for widget in [row, *row.winfo_children(), *text.winfo_children()]:
                widget.bind("<Button-1>", lambda event, s=sale: app.navigate("sale", sale_id=s["id"]))
        quick = panel(right)
        quick.pack(fill="x")
        label(quick, "Quick Actions", 18, True).pack(anchor="w", padx=18, pady=14)
        actions = ctk.CTkFrame(quick, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(0, 16))
        for i, (text, route, symbol, kind) in enumerate([
            ("Start New Sale", "pos", "cart", "soft"), ("Manage Products", "products", "box", "green"),
            ("Sales History", "sales", "receipt", "neutral"), ("View Audit Log", "audit", "shield", "neutral")]):
            actions.grid_columnconfigure(i % 2, weight=1, uniform="actions")
            widget = button(actions, text, lambda r=route: app.navigate(r), symbol, kind=kind, width=140)
            widget.configure(height=62)
            widget.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)
