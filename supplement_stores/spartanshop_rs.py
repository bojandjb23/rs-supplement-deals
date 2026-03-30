"""Scraper for suplementi-spartanshop.rs - WooCommerce supplement store."""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class SpartanShopScraper(BaseStoreScraper):
    STORE_NAME = "Spartan Shop"
    BASE_URL = "https://suplementi-spartanshop.rs"
    MAX_PAGES = 10  # Limit to first 10 pages (~160 products) for CI

    SALE_URL = "/shop/?filter_on-sale=1"

    # Map WooCommerce product_cat slugs to human-readable Serbian categories
    CATEGORY_MAP = {
        "proteini": "Proteini",
        "kreatin": "Kreatin",
        "aminokiseline": "Aminokiseline",
        "sagorevaci": "Sagorevaci Masti",
        "vitamini": "Vitamini",
        "minerali": "Minerali",
        "pre-workout": "Pre Workout",
        "fitnes-oprema": "Fitnes Oprema",
        "zdrava-hrana": "Zdrava Hrana",
    }

    def get_page_urls(self) -> List[str]:
        """Build paginated sale listing URLs, capped at MAX_PAGES."""
        first_url = f"{self.BASE_URL}{self.SALE_URL}"
        soup = self.fetch_page(first_url)
        if not soup:
            return [first_url]

        # Discover max page from pagination links
        max_page = 1
        pagination = soup.select(
            ".woocommerce-pagination a, a.page-numbers"
        )
        for link in pagination:
            text = link.get_text(strip=True)
            href = link.get("href", "")
            if text.isdigit():
                max_page = max(max_page, int(text))
            else:
                match = re.search(r"/page/(\d+)", href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)
        urls = []
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(first_url)
            else:
                urls.append(
                    f"{self.BASE_URL}/shop/page/{page}/?filter_on-sale=1"
                )
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract WooCommerce product card elements."""
        selectors = [
            "ul.products > li.product",
            "li.product",
            ".products .product",
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    def _extract_category(self, card: Tag) -> str:
        """Extract category from WooCommerce product_cat-* CSS class."""
        classes = card.get("class", [])
        for cls in classes:
            if cls.startswith("product_cat-"):
                slug = cls[len("product_cat-"):]
                return self.CATEGORY_MAP.get(slug, slug.replace("-", " ").title())
        return "Akcije"

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a WooCommerce product card from the sale listing."""
        # --- Product name ---
        name_el = card.select_one(
            ".woocommerce-loop-product__title, h2.product-title, h2"
        )
        name = self._find_text(name_el) if name_el else ""
        if not name:
            return None

        # --- Product URL ---
        product_url = ""
        link = card.select_one(
            "a.woocommerce-LoopProduct-link, "
            "a.woocommerce-loop-product__link, "
            "a[href*='/proizvod/']"
        )
        if link:
            product_url = self._find_attr(link, "href")
        if not product_url:
            first_link = card.select_one("a[href]")
            product_url = self._find_attr(first_link, "href")

        # --- Image URL ---
        image_url = self._find_image_url(card)

        # --- Prices ---
        # WooCommerce sale items: del (original) + ins (discount)
        # Many items on this store only show the sale price (no del/ins)
        original_price = None
        discount_price = None

        del_el = card.select_one("del")
        ins_el = card.select_one("ins")

        if del_el and ins_el:
            del_amount = del_el.select_one(".woocommerce-Price-amount")
            ins_amount = ins_el.select_one(".woocommerce-Price-amount")
            original_price = self.parse_price(
                self._find_text(del_amount) if del_amount else self._find_text(del_el)
            )
            discount_price = self.parse_price(
                self._find_text(ins_amount) if ins_amount else self._find_text(ins_el)
            )
        else:
            # Only sale price shown (original not displayed on listing).
            # Assign to original_price so the product has a usable price;
            # discount_percent will be 0 since we can't compute it without the original.
            price_amount = card.select_one(".woocommerce-Price-amount")
            if price_amount:
                original_price = self.parse_price(self._find_text(price_amount))

        # --- Category ---
        category = self._extract_category(card)

        # --- Stock status ---
        classes = " ".join(card.get("class", []))
        in_stock = "outofstock" not in classes
        if "Nema na zalihama" in card.get_text():
            in_stock = False

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
