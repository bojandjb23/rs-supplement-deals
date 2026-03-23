"""Scraper for amgsport.net - WooCommerce/Woodmart supplement store with 30+ brands."""

import re
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper


class AMGSportScraper(BaseStoreScraper):
    STORE_NAME = "AMG Sport"
    BASE_URL = "https://amgsport.net"
    SALE_URL = "https://amgsport.net/akcije/"
    MAX_PAGES = 10

    def __init__(self, session: Optional[requests.Session] = None, delay: float = None):
        super().__init__(session=session, delay=delay)
        # AMG Sport serves brotli-compressed responses when 'br' is in
        # Accept-Encoding, but requests can't decode brotli natively.
        # Remove 'br' to get gzip/deflate which requests handles fine.
        self.session.headers["Accept-Encoding"] = "gzip, deflate"

    def get_page_urls(self) -> List[str]:
        """Discover paginated sale pages.

        AMG Sport uses /akcije/page/N/ pagination (WooCommerce standard).
        Typically 4 pages with ~15 products each.
        """
        urls = [self.SALE_URL]
        soup = self.fetch_page(self.SALE_URL)
        if not soup:
            return urls

        max_page = 1
        pagination_links = soup.select(".page-numbers a, .woocommerce-pagination a")
        for link in pagination_links:
            text = link.get_text(strip=True)
            href = link.get("href", "")
            if text.isdigit():
                max_page = max(max_page, int(text))
            else:
                match = re.search(r"/page/(\d+)", href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)
        for page in range(2, max_page + 1):
            urls.append(f"{self.SALE_URL}page/{page}/")

        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract Woodmart product cards.

        Woodmart uses div.wd-product instead of the standard li.product.
        """
        selectors = [
            "div.wd-product",
            "li.product",
            ".products .product",
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a Woodmart/WooCommerce product card.

        Structure:
            div.wd-product (.instock/.outofstock in classes)
                div.wd-product-wrapper
                    div.wd-product-thumb
                        a.wd-product-img-link[href] -> product URL
                            div.product-labels > span.onsale -> "-45%"
                            img[src, srcset]
                    h3.wd-entities-title > a -> product name
                    div.wd-product-cats > a (multiple) -> categories
                    span.price
                        del > span.woocommerce-Price-amount -> original price
                        ins > span.woocommerce-Price-amount -> sale price
        """
        # Product name
        name_el = card.select_one("h3.wd-entities-title a, .woocommerce-loop-product__title, h2 a, h3 a")
        name = self._find_text(name_el)
        if not name:
            return None

        # Product URL
        product_url = ""
        link_el = card.select_one("a.wd-product-img-link, h3.wd-entities-title a, a[href]")
        if link_el:
            product_url = link_el.get("href", "")

        # Image URL
        image_url = self._find_image_url(card)

        # Prices
        original_price = None
        discount_price = None

        del_el = card.select_one("del .woocommerce-Price-amount, del .amount, del")
        ins_el = card.select_one("ins .woocommerce-Price-amount, ins .amount, ins")

        if del_el and ins_el:
            original_price = self.parse_price(self._find_text(del_el))
            discount_price = self.parse_price(self._find_text(ins_el))
        else:
            # Single price (no sale)
            price_el = card.select_one(".price .woocommerce-Price-amount, .price .amount, .price")
            if price_el:
                original_price = self.parse_price(self._find_text(price_el))

        # Category - from category links
        category = ""
        cat_links = card.select("div.wd-product-cats a, .product-category a, .posted_in a")
        if cat_links:
            # Use the first non-generic category
            skip = {"novi-proizvodi", "akcije", "sale"}
            for cat_link in cat_links:
                cat_text = self._find_text(cat_link)
                cat_href = cat_link.get("href", "")
                slug = cat_href.rstrip("/").rsplit("/", 1)[-1] if cat_href else ""
                if slug not in skip and cat_text:
                    category = cat_text
                    break
            if not category and cat_links:
                category = self._find_text(cat_links[0])

        # Stock status - checked from card's CSS classes
        card_classes = " ".join(card.get("class", []))
        in_stock = "outofstock" not in card_classes

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
