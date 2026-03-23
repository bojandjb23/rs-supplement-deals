"""Scraper for lama.rs - 30+ year old Belgrade supplement store (custom platform)."""

import re
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper


class LamaScraper(BaseStoreScraper):
    STORE_NAME = "LAMA"
    BASE_URL = "https://www.lama.rs"
    SALE_URL = "https://www.lama.rs/suplementi-na-akciji"

    def get_page_urls(self) -> List[str]:
        """LAMA loads all sale products on a single page - no pagination."""
        return [self.SALE_URL]

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards - each is a div.shopBoxProdN."""
        return soup.find_all("div", class_="shopBoxProdN")

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a LAMA product card.

        Structure:
            div.shopBoxProdN
                a[href] -> product link + image + discount badge
                    div.shopBoxProdImg > img.shopBoxProdIcn[src]
                    div.shopBoxTag4 -> "AKCIJA -50%"
                div.shopBoxProdTl
                    a > p.pTl -> product name
                    p.pTxt -> size/quantity
                div.priceProdN
                    p.saleProdN -> original price (crossed out)
                    p (no class) -> discount price
        """
        # Product name
        name_el = card.select_one("p.pTl")
        name = self._find_text(name_el)
        if not name:
            return None

        # Append size/quantity to name if present
        size_el = card.select_one("p.pTxt")
        size = self._find_text(size_el)
        if size:
            name = f"{name} {size}"

        # Product URL - from the title link
        title_link = card.select_one("div.shopBoxProdTl a[href]")
        if not title_link:
            # Fallback: first link with .html
            title_link = card.select_one("a[href$='.html']")
        product_url = self._find_attr(title_link, "href")

        # Image URL
        img = card.select_one("img.shopBoxProdIcn")
        image_url = self._find_attr(img, "src") if img else ""

        # Prices - inside div.priceProdN
        price_div = card.select_one("div.priceProdN")
        original_price = None
        discount_price = None

        if price_div:
            # Original price: p.saleProdN (struck through)
            original_el = price_div.select_one("p.saleProdN")
            original_price = self.parse_price(self._find_text(original_el))

            # Discount price: the <p> without .saleProdN class
            price_paragraphs = price_div.find_all("p")
            for p in price_paragraphs:
                if "saleProdN" not in (p.get("class") or []):
                    discount_price = self.parse_price(self._find_text(p))
                    break

        # Category - not available on the sale listing page
        category = ""

        # Stock status - if there's an add-to-cart button, it's in stock
        in_stock = card.select_one("div.shopBtnProdN") is not None

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
