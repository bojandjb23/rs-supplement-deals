"""Scraper for superior14.rs - Custom-built supplement store from Subotica/Novi Sad.

Superior14 carries 14+ brands and has a "super-ponuda" (super deal) section.
The weekly and monthly action pages (/nedeljna-akcija, /mesecna-akcija) are
often empty, so we scrape all three but handle empty results gracefully.

Product card structure (custom platform):
  section.products > div.blocks > div.block  (one per product)
    a[href] -> product link (wraps everything)
      figure.zoomzoom > img.lazyload[data-src] -> product image
      span.txt
        span.title -> product name
        span.tx -> description text
        span.price -> price (only one price shown, no old/original price on listings)

Note: Images use lazy loading with data-src containing the real URL and
src containing a base64 placeholder. Only a single price is shown on the
listing page (no original vs discount distinction available).
"""

import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class Superior14Scraper(BaseStoreScraper):
    STORE_NAME = "Superior14"
    BASE_URL = "https://www.superior14.rs"

    SALE_URLS = [
        "https://www.superior14.rs/proizvodi/super-ponuda/",
        "https://www.superior14.rs/proizvodi/nedeljna-akcija/",
        "https://www.superior14.rs/proizvodi/mesecna-akcija/",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_urls = set()

    def get_page_urls(self) -> List[str]:
        """Return all sale section URLs. No pagination on this site."""
        return list(self.SALE_URLS)

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards - each is a div.block inside div.blocks."""
        blocks_container = soup.select_one("div.blocks")
        if not blocks_container:
            return []
        return blocks_container.find_all("div", class_="block", recursive=False)

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a Superior14 product card.

        Structure:
            div.block
                a[href]  (wraps entire card)
                    figure.zoomzoom > img.lazyload[data-src, src(placeholder)]
                    span.txt
                        span.title  -> product name
                        span.tx     -> description
                        span.price  -> "5,990.00 RSD"
        """
        # Product link (wraps everything)
        link = card.find("a", href=True)
        if not link:
            return None

        product_url = self._find_attr(link, "href")

        # Deduplicate across sale sections
        url_key = product_url.rstrip("/")
        if url_key in self._seen_urls:
            return None
        self._seen_urls.add(url_key)

        # Product name
        title_el = card.select_one("span.title")
        name = self._find_text(title_el)
        if not name:
            return None

        # Image URL - uses lazy loading (data-src has the real URL)
        img = card.select_one("img.lazyload")
        image_url = ""
        if img:
            image_url = img.get("data-src", "") or img.get("src", "")
            # Skip base64 placeholder URLs
            if image_url.startswith("data:"):
                image_url = ""

        # Price - only a single price is shown on the listing page
        price_el = card.select_one("span.price")
        price = self.parse_price(self._find_text(price_el))

        # Since this is a "super-ponuda" / sale section, the listed price IS the
        # discount price. We don't have the original price from the listing page.
        original_price = price
        discount_price = None

        # Category from the product URL path
        # e.g. /proizvodi/proteini/product-slug/ -> "Proteini"
        category = "Akcija"
        if product_url:
            parts = product_url.strip("/").split("/")
            if len(parts) >= 2:
                cat_slug = parts[-2] if len(parts) >= 3 else parts[-1]
                # Clean up the slug to a readable category
                cat_name = cat_slug.replace("-", " ").title()
                if cat_name.lower() not in ("proizvodi", "super-ponuda", "nedeljna-akcija", "mesecna-akcija"):
                    category = cat_name

        # Stock - if listed in the sale section, assume in stock
        in_stock = True

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
