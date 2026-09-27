"""Focused product-grid regression check at two logical sizes and native DPI."""

from pathlib import Path
import sys
import traceback
import ctypes
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import customtkinter as ctk
from PIL import ImageGrab
from ui.app import ShopManager

app = ShopManager()
native_scale = app._get_window_scaling()
errors = []
app.report_callback_exception = lambda *args: errors.append("".join(traceback.format_exception(*args)))
output = Path(__file__).resolve().parents[1] / "artifacts"


def check(name):
    app.attributes("-topmost", True)
    app.lift()
    app.update()
    ctypes.windll.user32.RedrawWindow(app.winfo_id(), None, None, 0x585)
    time.sleep(.2)
    app.update()
    app.update_idletasks()
    page = app.page
    ImageGrab.grab(window=app.winfo_id()).save(output / f"{name}.png")
    app.attributes("-topmost", False)
    print(f"{name}: root={app.winfo_width()} grid={page.products_frame.winfo_width()} scale={page._get_widget_scaling()} columns={page.columns}", flush=True)
    tiles = page.products_frame.winfo_children()
    for tile in tiles:
        for widget in tile.winfo_children():
            assert widget.winfo_x() >= 0
            assert widget.winfo_x() + widget.winfo_width() <= tile.winfo_width(), (name, widget, tile.winfo_width())
    assert page._parent_canvas.yview()[0] == 0, page._parent_canvas.yview()
    print(f"{name}: {page.columns} columns; product content fits; page opens at top", flush=True)


def native():
    try:
        check("pos-small")
        ctk.set_widget_scaling(1)
        ctk.set_window_scaling(1)
        app.fit_screen()
        app.navigate("pos")
        app.after(1600, finish)
    except Exception:
        traceback.print_exc()
        app.destroy()
        sys.exit(1)


def finish():
    try:
        check("pos-native-dpi")
        assert not errors, errors
    except Exception:
        traceback.print_exc()
        app.destroy()
        sys.exit(1)
    app.destroy()


def small():
    try:
        check("pos")
        app.geometry("1180x720+0+0")
        app.after(1000, native)
    except Exception:
        traceback.print_exc()
        app.destroy()
        sys.exit(1)


def begin():
    ctk.set_widget_scaling(1 / native_scale)
    ctk.set_window_scaling(1 / native_scale)
    app.geometry("1440x940+0+0")
    app.navigate("pos")
    app.after(1600, small)


app.update()
app.after(100, begin)
app.mainloop()
