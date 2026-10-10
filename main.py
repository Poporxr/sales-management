"""Run the shop app with: python main.py."""

import config
import database
from ui.app import ShopApp


def main():
    # Database first: tables, then sample data on a fresh install.
    database.init_db()
    database.seed_if_empty()
    # Store details (name, address, phone) come from store.json.
    store_config = config.load_config()
    ShopApp(store_config).mainloop()


if __name__ == "__main__":
    main()
