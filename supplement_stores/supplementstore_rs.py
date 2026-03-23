"""Scraper for supplementstore.rs - Belgrade-based supplement store (OpenCart)."""

import re
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper


class SupplementStoreScraper(BaseStoreScraper):
    STORE_NAME = "Supplement Store"
    BASE_URL = "https://www.supplementstore.rs"
    MAX_PAGES = 10  # safety limit

    def get_page_urls(self) -> List[str]:
        """Discover paginated URLs from /akcija sale page.

        OpenCart pagination uses ?page=N. The pagination element shows
        total pages (e.g., 'Prikaz 1 do 12 od 29 (3 strana)').
        """
        first_url = f"{self.BASE_URL}/akcija"
        soup = self.fetch_page(first_url)
        if not soup:
            return [first_url]

        max_page = 1
        # OpenCart pagination: ul.pagination > li > a with ?page=N
        pagination = soup.select("ul.pagination a")
        for link in pagination:
            href = link.get("href", "")
            page_match = re.search(r"[?&]page=(\d+)", href)
            if page_match:
                max_page = max(max_page, int(page_match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)

        urls = []
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(first_url)
            else:
                urls.append(f"{first_url}?page={page}")
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract OpenCart product cards.

        Structure: div.product-layout > div.product-thumb
        Each card uses the 'product-list' layout class.
        """
        return soup.select("div.product-layout")

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse an OpenCart product card from supplementstore.rs /akcija.

        Card structure:
          div.product-layout.product-list.col-xs-12
            div.product-thumb
              div.image > a > img
              div.caption
                h4 > a  (name + URL)
                p  (description)
                div.availability > label  (stock status)
                p.price
                  span.price-new  (sale price, if discounted)
                  span.price-old  (original price, if discounted)
                  OR plain text  (single price, no discount)
        """
        # Product name
        name_el = card.select_one("h4 a")
        name = self._find_text(name_el)
        if not name:
            return None

        # Product URL (absolute, OpenCart uses <base> tag)
        product_url = self._find_attr(name_el, "href") if name_el else ""

        # Image
        img = card.select_one("div.image img")
        image_url = ""
        if img:
            image_url = img.get("src", "") or img.get("data-src", "")

        # Prices
        original_price = None
        discount_price = None

        price_new_el = card.select_one("span.price-new")
        price_old_el = card.select_one("span.price-old")

        if price_new_el and price_old_el:
            # Discounted product
            discount_price = self.parse_price(self._find_text(price_new_el))
            original_price = self.parse_price(self._find_text(price_old_el))
        else:
            # Single price (no discount shown, but it's on the akcija page)
            price_el = card.select_one("p.price")
            if price_el:
                original_price = self.parse_price(self._find_text(price_el))

        # Stock status
        in_stock = True
        stock_label = card.select_one("div.availability label")
        if stock_label:
            stock_text = self._find_text(stock_label).lower()
            if "nedostupno" in stock_text or "nema" in stock_text:
                in_stock = False

        return self.make_product(
            name=name,
            category="Akcija",
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
