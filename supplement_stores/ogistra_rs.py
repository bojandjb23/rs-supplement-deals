"""Scraper for ogistra-nutrition-shop.com - PrestaShop supplement store, 18 years established."""

import re
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper


class OgistraScraper(BaseStoreScraper):
    STORE_NAME = "Ogistra Nutrition"
    BASE_URL = "https://www.ogistra-nutrition-shop.com"
    SALE_URL = "https://www.ogistra-nutrition-shop.com/108-super-akcije"
    MAX_PAGES = 10

    def __init__(self, session: Optional[requests.Session] = None, delay: float = None):
        super().__init__(session=session, delay=delay)
        # Ogistra serves brotli-compressed responses when 'br' is in
        # Accept-Encoding, but requests can't decode brotli natively.
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def get_page_urls(self) -> List[str]:
        """Discover paginated sale pages.

        Ogistra uses ?page=N query parameter for pagination (PrestaShop style).
        Typically 3 pages with ~12 products each.
        """
        urls = [self.SALE_URL]
        soup = self.fetch_page(self.SALE_URL)
        if not soup:
            return urls

        max_page = 1
        pagination_links = soup.select("ul.page-list a, nav.pagination a, .pagination a")
        for link in pagination_links:
            text = link.get_text(strip=True)
            href = link.get("href", "")
            if text.isdigit():
                max_page = max(max_page, int(text))
            else:
                match = re.search(r"[?&]page=(\d+)", href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)
        for page in range(2, max_page + 1):
            urls.append(f"{self.SALE_URL}?page={page}")

        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract PrestaShop product miniature cards."""
        selectors = [
            "article.product-miniature",
            ".product-miniature",
            ".thumbnail-container",
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a PrestaShop product-miniature card.

        Structure:
            article.product-miniature[data-id-product]
                div.img_block
                    a.thumbnail.product-thumbnail[href] -> product URL
                        img.first-image[data-src] -> image (lazy loaded)
                    ul.product-flag
                        li.discount > span -> "-20%"
                div.product_desc
                    div.inner_desc
                        h3 > a.product_name[href, title] -> product name
                        div.product-price-and-shipping
                            span.regular-price -> original price
                            span.price.price-sale -> discount price
                            span.discount-percentage -> "-20%"
        """
        # Product name
        name_el = card.select_one("a.product_name, h3.product-title a, .product_name, h3 a")
        name = ""
        if name_el:
            # Prefer the title attribute (full name) over truncated text
            name = name_el.get("title", "") or self._find_text(name_el)
        if not name:
            return None

        # Product URL
        product_url = self._find_attr(name_el, "href") if name_el else ""
        if not product_url:
            thumb_link = card.select_one("a.thumbnail, a.product-thumbnail, a[href]")
            product_url = self._find_attr(thumb_link, "href")

        # Image URL - PrestaShop uses lazy loading with data-src
        image_url = ""
        img = card.select_one("img.first-image, img.product-image, img")
        if img:
            image_url = (
                img.get("data-src", "")
                or img.get("data-full-size-image-url", "")
                or img.get("src", "")
            )
            # Skip placeholder data URIs
            if image_url.startswith("data:"):
                image_url = img.get("data-src", "") or img.get("data-full-size-image-url", "")

        # Prices
        original_price = None
        discount_price = None

        regular_el = card.select_one("span.regular-price, .regular-price")
        sale_el = card.select_one("span.price-sale, span.price, .price")

        if regular_el and sale_el:
            original_price = self.parse_price(self._find_text(regular_el))
            discount_price = self.parse_price(self._find_text(sale_el))
        elif sale_el:
            # Only current price available (might not be on sale)
            original_price = self.parse_price(self._find_text(sale_el))

        # Category - not directly available on sale listing
        category = ""

        # Stock status - PrestaShop uses data attributes or CSS classes
        card_classes = " ".join(card.get("class", []))
        in_stock = "out-of-stock" not in card_classes and "unavailable" not in card_classes

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
