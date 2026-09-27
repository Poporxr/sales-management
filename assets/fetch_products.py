"""Optional asset preparation, not used by the application at runtime.

Photos are credited individually in sources.json. Retailer photos are used as
local training references, not licensed as original application artwork.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
QUERIES = {"coke": "Coca Cola Coke Pet Bottle 50", "pepsi": "Pepsi Pet Bottle",
           "fanta": "Fanta Orange Pet Bottle 50", "sprite": "Sprite Pet Bottle",
           "peak": "Peak Full Cream Milk Powder Tin 400", "indomie": "Indomie Chicken",
           "golden": "Golden Morn 500", "milo": "Milo Pouch", "dettol": "Dettol Original Soap",
           "closeup": "Close Up Red Hot 120", "bread": "Bread Loaf", "maggi": "Maggi Chicken"}


def get(url):
    with urlopen(Request(url, headers={"User-Agent": "ShopManagerTrainingPrototype/1.0"}), timeout=20) as response:
        return response.read()


def download(pair):
    key, query = pair
    params = urlencode({"q": query, "resources[type]": "product", "resources[limit]": 10})
    try:
        data = json.loads(get("https://www.supermart.ng/search/suggest.json?" + params))
        candidates = [p for p in data["resources"]["results"]["products"] if p.get("image")]
        terms = query.lower().split()
        def score(p):
            title = p["title"].lower()
            return sum(term in title for term in terms) * 3 - (4 if re.search(r"x\d", title) else 0)
        product = max(candidates, key=score)
        url = product["image"]
        (ROOT / "products" / f"{key}.jpg").write_bytes(get(url))
        print(f"Downloaded {key}", flush=True)
        return dict(asset=f"products/{key}.jpg", source=url, title=product["title"],
                    product_url="https://www.supermart.ng/products/" + product["handle"],
                    credit="Supermart.ng / respective product brands",
                    usage="Local educational prototype reference; no redistribution license claimed.")
    except Exception as error:
        print(f"No photo for {key}: {error}", flush=True)
        return next((s for s in PREVIOUS if s["asset"] == f"products/{key}.jpg"),
                    dict(asset=key, unavailable=True))


if __name__ == "__main__":
    PREVIOUS = json.loads((ROOT / "sources.json").read_text(encoding="utf-8")) if (ROOT / "sources.json").exists() else []
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(download, QUERIES.items()))
    (ROOT / "sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")
