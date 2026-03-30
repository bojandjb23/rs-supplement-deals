"""Scraper for proteinisi.rs (formerly rs.proteini.si) - WooCommerce / Woodmart theme.

The site migrated from rs.proteini.si to proteinisi.rs. The sale page is /akcija/.
Product cards are standard WooCommerce divs with class 'wd-product'.

Price structure (WooCommerce standard):
  <del> = original price
  <ins> = discounted (sale) price
  Both wrapped in <span class="woocommerce-Price-amount amount"><bdi>...

Category: extracted from CSS classes like product_cat-proteins -> "proteins"
"""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class ProteiniSiScraper(BaseStoreScraper):
    STORE_NAME = "Proteini.si"
    BASE_URL = "https://proteinisi.rs"
    SALE_URL = "https://proteinisi.rs/akcija/"

    def get_page_urls(self) -> List[str]:
        """Discover paginated sale page URLs.

        WooCommerce pagination uses /page/N/ path segments.
        """
        soup = self.fetch_page(self.SALE_URL)
        if not soup:
            return [self.SALE_URL]

        max_page = 1
        for a in soup.select(".page-numbers a, .woocommerce-pagination a"):
            href = a.get("href", "")
            m = re.search(r"/page/(\d+)/", href)
            if m:
                max_page = max(max_page, int(m.group(1)))

        urls = [self.SALE_URL]
        for page in range(2, max_page + 1):
            urls.append(f"{self.SALE_URL}page/{page}/")
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract WooCommerce product card divs."""
        cards = soup.select("div.wd-product")
        if cards:
            return cards
        # Fallback to generic WooCommerce product items
        return soup.select("li.product, div.product")

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a WooCommerce / Woodmart product card.

        Name:     .wd-product-title a, h2.woocommerce-loop-product__title a, or aria-label
        Image:    img.attachment-woocommerce_thumbnail src
        Prices:   .price del bdi (original) and .price ins bdi (sale)
        Category: product_cat-* CSS class on the card div
        """
        # Product name
        name = ""
        name_el = card.select_one(
            ".wd-product-title a, h2.woocommerce-loop-product__title, "
            "h3.woocommerce-loop-product__title, .product-title a"
        )
        if name_el:
            name = self._find_text(name_el)
        if not name:
            # Try aria-label on the image link
            img_link = card.select_one("a.product-image-link")
            if img_link:
                name = img_link.get("aria-label", "").strip()
        if not name:
            return None

        # Product URL
        product_url = ""
        link_el = card.select_one("a.product-image-link, .wd-product-title a, h2 a, h3 a")
        if link_el:
            product_url = link_el.get("href", "")

        # Image URL - prefer the primary (non-hover) thumbnail
        image_url = ""
        img = card.select_one("div.product-element-top > a img, img.attachment-woocommerce_thumbnail")
        if img:
            image_url = img.get("src", "") or img.get("data-src", "")

        # Prices from WooCommerce del/ins structure
        original_price = None
        discount_price = None
        price_el = card.select_one("span.price")
        if price_el:
            del_el = price_el.select_one("del bdi")
            ins_el = price_el.select_one("ins bdi")
            if del_el:
                original_price = self.parse_price(self._find_text(del_el))
            if ins_el:
                discount_price = self.parse_price(self._find_text(ins_el))
            # No sale: single price
            if not del_el and not ins_el:
                bdi = price_el.select_one("bdi")
                if bdi:
                    original_price = self.parse_price(self._find_text(bdi))

        # Discount badge percentage (fallback if prices not parsed)
        if not discount_price and original_price:
            badge = card.select_one("span.onsale")
            if badge:
                m = re.search(r"-?(\d+)%", self._find_text(badge))
                if m:
                    pct = int(m.group(1))
                    if pct > 0:
                        discount_price = round(original_price * (1 - pct / 100), 2)

        # Category from WooCommerce CSS classes (product_cat-<slug>)
        category = ""
        classes = " ".join(card.get("class", []))
        cat_match = re.search(r"product_cat-([\w-]+)", classes)
        if cat_match:
            slug = cat_match.group(1)
            if slug not in ("akcija", "sale", "uncategorized"):
                category = slug.replace("-", " ").title()

        # Stock status
        in_stock = "outofstock" not in classes

        return self.make_product(
            name=name,
            category=category or "Akcija",
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
