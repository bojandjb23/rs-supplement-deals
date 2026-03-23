"""Scraper for fitlab.rs - Nis-based supplement store (Next.js with RSC streaming).

Product data is NOT in traditional HTML elements. Instead, it is embedded as JSON
within React Server Component (RSC) streaming data inside self.__next_f.push() calls.

The sale page (/sr/akcija) contains an 'initialProducts' array in one of these push
calls. Each product has: id, name, slug, price, salePrice, discount, image, category,
brandName, isOnSale, inStock, etc.

Product URLs follow the pattern: https://fitlab.rs/sr/proizvodi/{slug}
Image URLs are relative paths starting with /products/...
"""

import re
import json
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class FitLabScraper(BaseStoreScraper):
    STORE_NAME = "FitLab"
    BASE_URL = "https://fitlab.rs"
    SALE_URL = "https://fitlab.rs/sr/akcija"

    def get_page_urls(self) -> List[str]:
        """Return the single sale page URL.

        All products are loaded at once via RSC streaming - no pagination needed.
        """
        return [self.SALE_URL]

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Not used - products come from JSON, not HTML cards.

        Returns empty list; scrape_all() is overridden to handle JSON extraction.
        """
        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Not used - products come from JSON, not HTML cards."""
        return None

    def _extract_products_from_rsc(self, html: str) -> List[Dict[str, Any]]:
        """Extract product data from Next.js RSC streaming data.

        The HTML contains script tags with self.__next_f.push([1, "RSC_DATA"])
        calls. One of these contains an 'initialProducts' key with a JSON array
        of product objects.

        In the raw HTML, quotes inside the push string are escaped as \"
        which Python reads as \\". We find the push call containing initialProducts,
        extract its string content, unescape it, then parse the JSON array.

        Returns a list of raw product dicts from the JSON.
        """
        # Search for 'initialProducts' (without surrounding quotes, since
        # the actual HTML has escaped quotes like \\"initialProducts\\")
        idx = html.find("initialProducts")
        if idx == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find initialProducts in HTML")
            return []

        # Find the enclosing self.__next_f.push([1,"..."]) call
        push_marker = 'self.__next_f.push([1,"'
        push_start = html.rfind(push_marker, max(0, idx - 5000))
        if push_start == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find push call for initialProducts")
            return []

        # Content starts after the opening quote of the push string
        content_start = push_start + len(push_marker)

        # The push call ends with "]) before </script>
        # Find </script> after the push_start
        script_end = html.find("</script>", push_start)
        if script_end == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find </script> after push call")
            return []

        # The string content ends just before the closing "])
        # which appears right before </script>
        content_end = html.rfind('"])', content_start, script_end + 1)
        if content_end == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find end of push call string")
            return []

        raw_string = html[content_start:content_end]

        # Unescape: the push string has \" for quotes and \\\\ for backslashes
        # In Python's string representation: \\" -> " and \\\\\\\\ -> \\
        unescaped = raw_string.replace('\\"', '"').replace('\\\\', '\\')

        # Find the initialProducts JSON array in the unescaped content
        prod_idx = unescaped.find('"initialProducts":')
        if prod_idx == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find initialProducts key after unescaping")
            return []

        array_start = unescaped.find("[{", prod_idx)
        if array_start == -1:
            logger.warning(f"[{self.STORE_NAME}] Could not find product array start")
            return []

        # Find the matching closing bracket by counting depth
        depth = 0
        end_pos = array_start
        for j in range(array_start, len(unescaped)):
            if unescaped[j] == "[":
                depth += 1
            elif unescaped[j] == "]":
                depth -= 1
                if depth == 0:
                    end_pos = j
                    break

        products_json = unescaped[array_start : end_pos + 1]

        try:
            products = json.loads(products_json)
            logger.info(f"[{self.STORE_NAME}] Extracted {len(products)} products from RSC data")
            return products
        except json.JSONDecodeError as e:
            logger.error(f"[{self.STORE_NAME}] Failed to parse products JSON: {e}")
            return []

    def _product_from_json(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a raw FitLab product JSON object to a standardized product dict.

        Expected fields:
          - id: int
          - name: str
          - slug: str
          - price: int (original price in RSD)
          - salePrice: int or "$undefined" (discounted price)
          - discount: str like "-30%" or "$undefined"
          - image: str (relative path like /products/2023/01/...)
          - category: str
          - brandName: str
          - isOnSale: bool
          - inStock: bool
        """
        name = item.get("name", "")
        if not name:
            return None

        slug = item.get("slug", "")
        product_url = f"{self.BASE_URL}/sr/proizvodi/{slug}" if slug else ""

        # Image URL - relative, needs base URL prepended
        image_path = item.get("image", "")
        image_url = f"{self.BASE_URL}{image_path}" if image_path else ""

        # Prices
        original_price = None
        discount_price = None

        price_val = item.get("price")
        if isinstance(price_val, (int, float)):
            original_price = float(price_val)

        sale_val = item.get("salePrice")
        if isinstance(sale_val, (int, float)):
            discount_price = float(sale_val)
        # "$undefined" or None means no sale price

        # Category
        category = item.get("category", "")
        if not category or category == "Akcija":
            # Try to get more specific category from categorySlugs
            slugs = item.get("categorySlugs", [])
            for s in slugs:
                if s != "akcija":
                    category = s.replace("-", " ").title()
                    break
            if not category:
                category = "Akcija"

        # Stock status
        in_stock = item.get("inStock", True)

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Override base scrape_all to extract products from Next.js RSC JSON data.

        Instead of parsing HTML cards, we:
        1. Fetch the sale page HTML
        2. Extract the initialProducts JSON from RSC streaming data
        3. Convert each product JSON object to our standardized format
        """
        self.products = []

        logger.info(f"[{self.STORE_NAME}] Fetching sale page: {self.SALE_URL}")

        # We need the raw HTML, not BeautifulSoup - fetch directly
        self._rate_limit()
        try:
            response = self.session.get(self.SALE_URL, timeout=30)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            logger.error(f"[{self.STORE_NAME}] Failed to fetch {self.SALE_URL}: {e}")
            return self.products

        raw_products = self._extract_products_from_rsc(html)

        for item in raw_products:
            try:
                product = self._product_from_json(item)
                if product and product.get("name"):
                    self.products.append(product)
            except Exception as e:
                logger.warning(
                    f"[{self.STORE_NAME}] Failed to parse product: {e}"
                )

        logger.info(f"[{self.STORE_NAME}] Scraped {len(self.products)} products")
        return self.products
