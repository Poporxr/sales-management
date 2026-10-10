"""The main window: sidebar navigation plus a content area.

Navigation is deliberately simple: navigate() destroys the current page
and builds the new one from scratch. Every screen therefore always
shows fresh data, and there is no cache-invalidation logic for the
owner to explain to a supervisor.
"""

import customtkinter as ctk

from ui import theme as T
from ui.widgets import label


class ShopApp(ctk.CTk):
    def __init__(self, config):
        super().__init__()
        ctk.set_appearance_mode("light")
        self.title("Shop Manager")
        self.geometry("1280x800")
        self.minsize(1000, 640)
        self.configure(fg_color=T.BG)

        self.config = config          # store.json details
        self.cashier = None           # chosen on the welcome screen
        self.page = None              # the currently visible page
        self.nav_buttons = {}

        # Sidebar: fixed width, dark, holds the brand and nav buttons.
        sidebar = ctk.CTkFrame(self, width=220, fg_color=T.NAV, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(28, 32))
        label(brand, config["store_name"], 19, True, T.WHITE).pack(anchor="w")
        label(brand, "Shop Manager", 11, color=T.NAV_TEXT).pack(anchor="w")

        # (page key, button label). The welcome screen is not in the sidebar.
        for key, text in [("home", "Home"), ("pos", "New Sale"),
                          ("products", "Products"), ("history", "Sales History"),
                          ("audit", "Audit Log")]:
            btn = ctk.CTkButton(sidebar, text=text,
                                command=lambda k=key: self.navigate(k),
                                fg_color="transparent", text_color=T.NAV_TEXT,
                                hover_color=T.NAV_ACTIVE, anchor="w",
                                font=T.font(15), height=46, corner_radius=8)
            btn.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = btn

        # Cashier name sits at the bottom of the sidebar.
        self.cashier_label = label(sidebar, "", 12, color=T.NAV_TEXT)
        self.cashier_label.pack(side="bottom", pady=18)

        # Content area: pages are built inside this frame.
        self.content = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        self.content.pack(side="right", fill="both", expand=True)

        self.navigate("welcome")

    def navigate(self, name):
        """Show a page. The old page is destroyed first, so screens can
        never show stale data."""
        # Local imports avoid circular imports: pages import nothing from app.
        from ui.pages.home import HomePage
        from ui.pages.pos import PosPage
        from ui.pages.products import ProductsPage
        from ui.pages.history import HistoryPage
        from ui.pages.audit import AuditPage
        from ui.pages.welcome import WelcomePage
        pages = {"welcome": WelcomePage, "home": HomePage, "pos": PosPage,
                 "products": ProductsPage, "history": HistoryPage,
                 "audit": AuditPage}
        if self.page is not None:
            self.page.destroy()
        self.page = pages[name](self)
        self.page.pack(fill="both", expand=True, padx=24, pady=24)
        # Highlight the active sidebar button.
        for key, btn in self.nav_buttons.items():
            active = (key == name)
            btn.configure(fg_color=T.NAV_ACTIVE if active else "transparent",
                          text_color=T.WHITE if active else T.NAV_TEXT)

    def set_cashier(self, name):
        """Called by the welcome screen once someone picks a name."""
        self.cashier = name
        self.cashier_label.configure(text="Cashier: " + name)
        self.navigate("home")
