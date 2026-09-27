"""Run with .venv/Scripts/python tests/ui_smoke.py on a Windows desktop."""

from pathlib import Path
import sys
import traceback
import ctypes
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
import customtkinter as ctk
from ui.app import ShopManager
from ui.components.dialogs import SaleCompletedDialog

OUTPUT = Path(__file__).resolve().parents[1] / "artifacts"
OUTPUT.mkdir(exist_ok=True)
app = ShopManager()
scale = app._get_window_scaling()
ctk.set_widget_scaling(1 / scale)
ctk.set_window_scaling(1 / scale)
errors = []
app.report_callback_exception = lambda *error: errors.append("".join(traceback.format_exception(*error)))


def capture(name):
    app.attributes("-topmost", True)
    app.lift()
    app.update_idletasks()
    app.update()
    ctypes.windll.user32.RedrawWindow(app.winfo_id(), None, None, 0x585)
    time.sleep(.2)
    app.update()
    # Capture only this window, even while another application is in front.
    ImageGrab.grab(window=app.winfo_id()).save(OUTPUT / f"{name}.png")
    app.attributes("-topmost", False)


def run():
    try:
        app.geometry("1440x940+0+0")
        capture("home")
        for route, params in [("pos", {}), ("sales", {}), ("sale", {"sale_id": "000048"}),
                              ("audit", {}), ("log", {"log_id": "000124"}),
                              ("product", {"product_id": 1}), ("products", {})]:
            app.navigate(route, **params)
            capture(route)
            assert app.page.winfo_exists() and app.page.winfo_ismapped(), route
            print(f"Rendered {route}", flush=True)
        # Alternate document IDs and revisit them: cache eviction must never
        # destroy the newly opened product, receipt, or audit detail page.
        for route, field, ids in [("product", "product_id", [1, 2, 1]),
                                  ("sale", "sale_id", ["000048", "000047", "000048"]),
                                  ("log", "log_id", ["000124", "000123", "000124"])]:
            for identifier in ids:
                app.navigate(route, **{field: identifier})
                app.update()
                assert app.page.winfo_exists() and app.page.winfo_ismapped(), (route, identifier)
                assert app.page.body.winfo_width() > 100
        app.navigate("product", product_id=1)
        for tab in ["Stock History", "Price History", "Sales History", "Overview"]:
            app.page.show_tab(tab)
            app.update()
        app.page._parent_canvas.event_generate("<MouseWheel>", delta=-120)
        app.update()
        app.navigate("sales")
        app.page.query.set("Peak")
        assert app.page.filtered and all(any("Peak" in p["name"] for p in s["items"]) for s in app.page.filtered)
        app.page.query.set("not-a-product")
        assert not app.page.filtered
        app.page.query.set("")
        app.page.move(1)
        assert app.page.page_number == 2
        app.navigate("pos")
        app.page.query.set("5449000000996")
        app.page.scan()
        assert app.store.cart[1] == 3
        app.page.change_quantity(1, -1)
        app.page.hold()
        assert not app.store.cart
        app.page.hold()
        assert app.store.cart[1] == 2
        dialog = app.page.checkout()
        app.update()
        capture("checkout")
        dialog.amount.delete(0, "end")
        dialog.amount.insert(0, "1")
        dialog.complete()
        assert dialog.winfo_exists()
        dialog.amount.delete(0, "end")
        dialog.amount.insert(0, "6000")
        dialog.complete()
        assert app.route == "pos" and len(app.store.sales) == 49
        success = next(w for w in app.winfo_children() if isinstance(w, SaleCompletedDialog))
        success.close()
        assert app.store.sales[0]["total"] == 5400
        app.geometry("1180x720+0+0")
        for route, params in [("home", {}), ("pos", {}), ("sales", {}), ("audit", {}),
                              ("sale", {"sale_id": "000048"}), ("product", {"product_id": 1}),
                              ("log", {"log_id": "000124"})]:
            app.navigate(route, **params)
            app.clear_toast()
            capture(route + "-small")
        if errors:
            raise AssertionError("\n".join(errors))
        print("UI smoke passed: navigation, product tabs, search, pagination, barcode, hold/resume, checkout, two window sizes.", flush=True)
    except Exception:
        traceback.print_exc()
        app.destroy()
        sys.exit(1)
    app.destroy()


app.update()
app.after(1200, run)
app.mainloop()
