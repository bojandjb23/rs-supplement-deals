"""Scraper for titaniumsport.rs - WooCommerce (XStore theme) supplement store."""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class TitaniumSportScraper(BaseStoreScraper):
    STORE_NAME = "TitaniumSport"
    BASE_URL = "https://www.titaniumsport.rs"
    MAX_PAGES = 10

    SALE_URL = "/product-category/akcije/"

    def get_page_urls(self) -> List[str]:
        """Discover paginated URLs from the akcije (sale) category."""
        urls = []
        first_url = f"{self.BASE_URL}{self.SALE_URL}"
        soup = self.fetch_page(first_url)
        if not soup:
            return [first_url]

        # Find max page from pagination links
        max_page = 1
        pagination = soup.select('.page-numbers a, .woocommerce-pagination a, a.page-numbers')
        for link in pagination:
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text.isdigit():
                max_page = max(max_page, int(text))
            else:
                match = re.search(r'/page/(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(first_url)
            else:
                urls.append(f"{first_url}page/{page}/")

        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards from WooCommerce listing."""
        selectors = [
            'li.product',
            '.products .product',
            'ul.products > li',
            '.product-grid .product',
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a WooCommerce/XStore product card from the akcije page."""
        # Product name: look for WooCommerce title, h2, or first meaningful link text
        name = ""
        name_el = card.select_one(
            '.woocommerce-loop-product__title, '
            'h2.product-title, h2, h3, '
            '.product-title'
        )
        if name_el:
            name = self._find_text(name_el)

        # If no name from heading, try the first link with product URL
        if not name:
            for a in card.select('a[href]'):
                href = a.get('href', '')
                if '/proizvod/' in href:
                    text = self._find_text(a)
                    if text and len(text) > 2:
                        name = text
                        break

        if not name:
            return None

        # Product URL: first link containing /proizvod/
        product_url = ""
        for a in card.select('a[href]'):
            href = a.get('href', '')
            if '/proizvod/' in href:
                product_url = href
                break
        if not product_url:
            link = card.select_one('a[href]')
            product_url = self._find_attr(link, 'href')

        # Image URL
        image_url = self._find_image_url(card)

        # Prices: WooCommerce uses del (original) and ins (sale)
        original_price = None
        discount_price = None

        del_el = card.select_one('del')
        ins_el = card.select_one('ins')

        if del_el and ins_el:
            # Get the first Price-amount inside del and ins for clean text
            del_amount = del_el.select_one('.woocommerce-Price-amount')
            ins_amount = ins_el.select_one('.woocommerce-Price-amount')
            original_price = self.parse_price(
                self._find_text(del_amount) if del_amount else self._find_text(del_el)
            )
            discount_price = self.parse_price(
                self._find_text(ins_amount) if ins_amount else self._find_text(ins_el)
            )
        else:
            # No del/ins: try first individual Price-amount span
            price_amount = card.select_one('.woocommerce-Price-amount')
            if price_amount:
                original_price = self.parse_price(self._find_text(price_amount))

        # Stock status
        classes = ' '.join(card.get('class', []))
        in_stock = 'outofstock' not in classes
        # Also check for "Nema na zalihama" text
        stock_text = card.get_text()
        if 'Nema na zalihama' in stock_text:
            in_stock = False

        return self.make_product(
            name=name,
            category="Akcije",
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
