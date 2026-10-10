"""Store details live in store.json, not in the code.

The app creates the file with sensible defaults on first run, so the
owner can change the shop name, address and phone without touching
any Python. Every screen that shows store details reads from here.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store.json")

DEFAULTS = {
    "store_name": "Main Store",
    "address": "12 Market Road, Lagos",
    "phone": "0800 000 0000",
    "receipt_footer": "Thank you for shopping with us!",
}


def load_config():
    """Return the store details dict, creating store.json first if missing."""
    if not os.path.exists(CONFIG_PATH):
        # First run: write the defaults so the owner has a file to edit.
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=2)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    # If the owner deleted a key by accident, fall back to the default
    # instead of crashing.
    for key, value in DEFAULTS.items():
        config.setdefault(key, value)
    return config
