"""Welcome screen: picks who is using the till today.

The chosen name is stamped on every sale and audit entry, so the
audit log always shows who did what. No passwords here, this is a
demo; the manager PIN still guards the sensitive actions.
"""

import customtkinter as ctk

from ui import theme as T
from ui.widgets import label, button, card


class WelcomePage(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app.content, fg_color="transparent")
        self.app = app

        box = card(self)
        box.place(relx=0.5, rely=0.5, anchor="center")
        inner = ctk.CTkFrame(box, fg_color="transparent")
        inner.pack(padx=60, pady=48)

        label(inner, app.config["store_name"], 26, True).pack(pady=(0, 4))
        label(inner, "Who is using the till today?", 15,
              color=T.MUTED).pack(pady=(0, 24))

        for name in ["Admin", "Cashier 1", "Cashier 2"]:
            button(inner, name, lambda n=name: app.set_cashier(n),
                   width=260).pack(pady=6)
