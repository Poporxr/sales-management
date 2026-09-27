"""One desktop window and a persistent sidebar."""

import customtkinter as ctk
import sys
from services.mock_store import MockStore
from ui import theme as T
from ui.components.widgets import icon, label


class ShopManager(ctk.CTk):
    # Keep Windows' light title bar instead of CTk's withdraw/redraw workaround.
    _deactivate_windows_window_header_manipulation = True

    def __init__(self):
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("Shop Manager")
        self.fit_screen()
        self.configure(fg_color=T.BG)
        self.store = MockStore()
        self.page = None
        self.pages = {}
        self.drawer = None
        self.toast_widget = None
        self.toast_job = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        sidebar = ctk.CTkFrame(self, width=222, fg_color=T.NAV, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(28, 36))
        label(brand, "", image=icon("store", "#68AEFF", 34)).pack(side="left", padx=(0, 10))
        texts = ctk.CTkFrame(brand, fg_color="transparent")
        texts.pack(side="left")
        label(texts, "Shop Manager", 19, True, T.WHITE).pack(anchor="w")
        label(texts, "Store Management System", 10, color=T.NAV_TEXT).pack(anchor="w")
        self.nav_buttons = {}
        for index, (key, text, symbol) in enumerate([
            ("home", "Home", "home"), ("pos", "New Sale", "cart"),
            ("products", "Products", "box"), ("sales", "Sales History", "receipt"),
            ("audit", "Audit Log", "shield"), ("settings", "Settings", "settings")], 1):
            nav = ctk.CTkButton(sidebar, text=text, image=icon(symbol, T.NAV_TEXT, 25),
                                anchor="w", compound="left", command=lambda k=key: self.navigate(k),
                                font=T.font(16), height=52, corner_radius=8, border_spacing=14,
                                fg_color="transparent", text_color=T.NAV_TEXT, hover_color=T.NAV_ACTIVE)
            nav.grid(row=index, column=0, sticky="ew", padx=13, pady=4)
            self.nav_buttons[key] = nav
        footer = ctk.CTkFrame(sidebar, fg_color="#20394F", corner_radius=8)
        footer.grid(row=9, column=0, sticky="ew", padx=14, pady=20)
        label(footer, "", image=icon("store", T.NAV_TEXT, 28)).pack(side="left", padx=12)
        foot_text = ctk.CTkFrame(footer, fg_color="transparent")
        foot_text.pack(side="left", pady=14)
        label(foot_text, "Main Store", 14, True, T.WHITE).pack(anchor="w")
        label(foot_text, "Offline session", 11, color=T.NAV_TEXT).pack(anchor="w")
        label(footer, "", width=9, height=9, fg_color="#26CA78", corner_radius=5).pack(side="right", padx=12)
        self.content = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.navigate("home")

    def fit_screen(self):
        width, height = self.winfo_screenwidth(), self.winfo_screenheight()
        if sys.platform == "win32":
            import ctypes
            from ctypes.wintypes import RECT
            work_area = RECT()
            # Tk can cache pre-DPI-awareness screen dimensions on Windows.
            if ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(work_area), 0):
                width, height = work_area.right - work_area.left, work_area.bottom - work_area.top
        scale = self._get_window_scaling()
        width = min(1440, int((width - 70) / scale))
        height = min(940, int((height - 70) / scale))
        self.minsize(min(1100, width), min(620, height))
        self.geometry(f"{width}x{height}+20+20")

    def navigate(self, route, **params):
        from ui.pages.home import HomePage
        from ui.pages.pos import SalePage
        from ui.pages.history import HistoryPage
        from ui.pages.details import ProductDetails, SaleDetails, AuditDetails
        from ui.pages.products import ProductsPage
        if route == "settings":
            self.toast("Settings is reserved.", "info")
            return
        routes = {"home": HomePage, "pos": SalePage, "products": ProductsPage,
                  "sales": HistoryPage, "audit": HistoryPage,
                  "product": ProductDetails, "sale": SaleDetails, "log": AuditDetails}
        self.close_drawer()
        # Pages are built lazily, then reused. In particular POS keeps its search,
        # scroll positions, images, and cart widgets when navigating away and back.
        key = (route, tuple(sorted(params.items())))
        cached = self.pages.get(key)
        stale = cached and cached[1] != self.store.revision and route not in ("pos", "products")
        old_page = self.page
        obsolete = None
        if cached is None or stale:
            arguments = dict(params)
            if route == "audit":
                arguments["audit"] = True
            new_page = routes[route](self, **arguments)
            if cached:
                obsolete = cached[0]
            self.pages[key] = (new_page, self.store.revision)
        else:
            new_page = cached[0]
            if hasattr(new_page, "refresh"):
                new_page.refresh()
        self.route = route
        self.route_params = params
        active = {"product": "products", "sale": "sales", "log": "audit"}.get(route, route)
        for nav_key, widget in self.nav_buttons.items():
            widget.configure(fg_color=T.NAV_ACTIVE if nav_key == active else "transparent",
                             text_color=T.WHITE if nav_key == active else T.NAV_TEXT)
        self.page = new_page
        self.page.grid(row=0, column=0, sticky="nsew")
        if old_page is not None and old_page is not new_page:
            old_page.grid_remove()
        if obsolete is not None:
            obsolete.destroy()
        # Keep only the most recent document of each kind. Main workspaces stay
        # cached, but opening hundreds of receipts must not retain every widget.
        if route in ("product", "sale", "log"):
            # Compare against the route cache key, never a sidebar button key:
            # deleting the current document here leaves the content area blank.
            for previous_key in list(self.pages):
                if previous_key[0] == route and previous_key != key:
                    previous_page, _ = self.pages.pop(previous_key)
                    previous_page.destroy()

    def data_changed(self):
        """Refresh only live collection views; reports check revision on return."""
        for (route, _), (page, _) in self.pages.items():
            if route in ("pos", "products"):
                page.refresh()

    def open_log(self, log_id):
        from ui.components.audit_drawer import AuditDrawer
        self.close_drawer()
        self.drawer = AuditDrawer(self, log_id)
        self.drawer.place(relx=1, rely=0, relheight=1, anchor="ne")
        self.drawer.lift()

    def close_drawer(self):
        if self.drawer is not None:
            self.drawer.destroy()
            self.drawer = None

    def toast(self, message, tone="info"):
        if self.toast_job:
            self.after_cancel(self.toast_job)
        if self.toast_widget:
            self.toast_widget.destroy()
        colors = {"info": T.INK, "success": T.GREEN, "error": T.RED, "warning": T.AMBER}
        self.toast_widget = ctk.CTkLabel(self, text=message, text_color=T.WHITE,
                                        fg_color=colors[tone], corner_radius=8, font=T.font(13),
                                        padx=22, pady=14, wraplength=600)
        self.toast_widget.place(relx=.59, rely=.94, anchor="s")
        self.toast_widget.lift()
        self.toast_job = self.after(4500, self.clear_toast)

    def clear_toast(self):
        if self.toast_widget:
            self.toast_widget.destroy()
            self.toast_widget = None
        self.toast_job = None
