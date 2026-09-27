"""Native UI regression: block sockets, exercise forms, and check widget reuse."""

from pathlib import Path
import ctypes
import socket
import sys
import time
import traceback
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from PIL import ImageGrab
from ui.app import ShopManager
from ui.components.dialogs import ManagerDialog, SaleCompletedDialog
from ui.components.product_dialogs import ProductDialog, StockDialog

OUT = Path(__file__).resolve().parents[1] / "artifacts" / "batch-two"
OUT.mkdir(parents=True, exist_ok=True)
network_calls = []


def no_network(*args, **kwargs):
    network_calls.append(args)
    raise AssertionError("Network access is forbidden in this offline test.")


# Deny connections and DNS even if a future import accidentally adds a client.
patchers = [patch.object(socket.socket, "connect", no_network),
            patch.object(socket, "create_connection", no_network),
            patch.object(socket, "getaddrinfo", no_network)]
for patcher in patchers:
    patcher.start()
app = ShopManager()
errors = []
app.report_callback_exception = lambda *args: errors.append("".join(traceback.format_exception(*args)))
scale = app._get_window_scaling()
ctk.set_widget_scaling(1 / scale)
ctk.set_window_scaling(1 / scale)


def settle():
    app.update_idletasks()
    app.update()


def capture(name, window=None):
    window = window or app
    window.attributes("-topmost", True)
    window.lift()
    settle()
    handle = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)
    ctypes.windll.user32.RedrawWindow(handle, None, None, 0x585)
    time.sleep(.25)
    settle()
    picture = ImageGrab.grab(window=handle)
    assert picture.convert("L").getextrema()[1] - picture.convert("L").getextrema()[0] > 30, (name, window.state())
    picture.save(OUT / f"{name}.png")
    window.attributes("-topmost", False)


def set_entry(widget, value):
    widget.delete(0, "end")
    widget.insert(0, str(value))


def authorize():
    dialog = next(w for w in app.winfo_children() if isinstance(w, ManagerDialog))
    set_entry(dialog.pin, "0000")
    dialog.authorize()
    assert dialog.winfo_exists()
    capture("manager-authorization", dialog)
    set_entry(dialog.pin, "1234")
    dialog.authorize()


def run():
    try:
        app.geometry("1440x900+0+0")
        start = time.perf_counter()
        app.navigate("pos")
        settle()
        pos = app.page
        print(f"First POS build: {time.perf_counter()-start:.3f}s", flush=True)
        rows = dict(pos.cart_rows)
        tiles = dict(pos.tiles)
        footer = pos.discount_entry
        footer.insert(0, "SAVE10")
        start = time.perf_counter()
        for _ in range(20):
            pos.change_quantity(1, 1)
            pos.change_quantity(1, -1)
        elapsed = time.perf_counter() - start
        assert all(pos.cart_rows[pid] is row for pid, row in rows.items())
        assert pos.tiles == tiles and pos.discount_entry is footer
        assert footer.get() == "SAVE10"
        pos.remove(9)
        assert pos.cart_rows[1] is rows[1] and 9 not in pos.cart_rows
        pos.change_quantity(9, 1)
        print(f"40 incremental cart updates: {elapsed:.3f}s; row/tile/input identities preserved", flush=True)
        pos.products_frame._parent_canvas.yview_moveto(.6)
        settle()
        product_scroll = pos.products_frame._parent_canvas.yview()
        pos.cart_scroll._parent_canvas.yview_moveto(.5)
        settle()
        assert pos.products_frame._parent_canvas.yview() == product_scroll
        capture("new-sale")
        app.navigate("products")
        capture("products")
        start = time.perf_counter()
        app.navigate("pos")
        assert app.page is pos
        print(f"Cached POS navigation: {time.perf_counter()-start:.3f}s", flush=True)
        app.navigate("products")
        dialog = ProductDialog(app)
        for field, value in dict(name="Offline Test Product", barcode="LOCAL-TEST", cost=80, price=120, stock=15, minimum=3).items():
            set_entry(dialog.fields[field], value)
        dialog.update_status()
        with patch("ui.components.product_dialogs.filedialog.askopenfilename",
                   return_value=str(Path(__file__).resolve().parents[1] / "assets/products/coke.jpg")):
            dialog.upload_image()
        assert dialog.image_key.startswith("upload-")
        capture("add-product", dialog)
        dialog.save()
        added = app.store.products[-1]
        assert added["name"] == "Offline Test Product"
        product_id = added["id"]
        edit = ProductDialog(app, product_id)
        set_entry(edit.fields["price"], 150)
        edit.save()
        assert added["price"] == 120
        authorize()
        assert added["price"] == 150
        # Dismissing authorization must leave the original form and data intact.
        cancelled = ProductDialog(app, product_id)
        set_entry(cancelled.fields["price"], 999)
        cancelled.save()
        guard = next(w for w in app.winfo_children() if isinstance(w, ManagerDialog))
        guard.close()
        assert added["price"] == 150 and cancelled.winfo_exists()
        cancelled.close()
        stock = StockDialog(app, 1)
        set_entry(stock.quantity, 12)
        stock.reason.set("Restock from supplier")
        stock.update_preview()
        capture("adjust-stock", stock)
        stock.save()
        assert app.store.product(1)["stock"] == 24
        authorize()
        assert app.store.product(1)["stock"] == 36
        app.navigate("audit")
        app.open_log(app.store.logs[0]["id"])
        capture("stock-log-drawer")
        table_page = app.page
        app.close_drawer()
        assert app.page is table_page
        app.open_log("000124")
        capture("sale-log-drawer")
        app.navigate("pos")
        checkout = pos.checkout()
        set_entry(checkout.amount, "1")
        checkout.complete()
        assert checkout.winfo_exists()
        set_entry(checkout.amount, 6000)
        checkout.update_change()
        capture("checkout", checkout)
        checkout.complete()
        success = next(w for w in app.winfo_children() if isinstance(w, SaleCompletedDialog))
        assert not app.store.cart and app.page is pos
        capture("sale-completed", success)
        success.close()
        app.geometry("1180x720+0+0")
        app.after(500, finish_small)
    except Exception:
        fail()


def finish_small():
    try:
        capture("new-sale-small")
        pos = app.page
        for tile in pos.tiles.values():
            for child in tile.winfo_children():
                assert child.winfo_x() + child.winfo_width() <= tile.winfo_width() + 2
        assert pos.complete_button.winfo_rooty() + pos.complete_button.winfo_height() <= app.winfo_rooty()+app.winfo_height()
        app.navigate("products")
        capture("products-small")
        dialog = ProductDialog(app)
        capture("add-product-small", dialog)
        dialog.close()
        assert not errors, "\n".join(errors)
        assert not network_calls
        print("PASS: offline workflows, authorization, snapshots, independent scrolling, widget reuse, and two window sizes.", flush=True)
        app.destroy()
    except Exception:
        fail()


def fail():
    traceback.print_exc()
    app.destroy()
    sys.exit(1)


app.update()
app.after(1200, run)
app.mainloop()
