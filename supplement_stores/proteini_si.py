"""Scraper for rs.proteini.si - Regional supplement store (Slovenia-based, serves Serbia)."""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class ProteiniSiScraper(BaseStoreScraper):
    STORE_NAME = "Proteini.si"
    BASE_URL = "https://rs.proteini.si"

    SALE_URL = "/lista-proizvoda/discount"

    def get_page_urls(self) -> List[str]:
        """Return the discount page URL.

        The discount page at rs.proteini.si/lista-proizvoda/discount appears to show
        all sale items on a single page (no observed pagination controls).
        """
        return [f"{self.BASE_URL}{self.SALE_URL}"]

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards from the discount listing.

        Products are identified by h4 > a links with product URLs,
        and associated price blocks with AKCIJSKA CENA / REDOVNA CENA labels.
        We look for repeating card-like containers.
        """
        # Try common card container selectors
        selectors = [
            '.product-card',
            '.product-item',
            '.product-box',
            '[class*="product"]',
            '.item',
            '.card',
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if len(cards) >= 2:
                # Verify these actually contain product data (price text)
                valid = [c for c in cards if 'AKCIJSKA CENA' in c.get_text() or 'REDOVNA CENA' in c.get_text()]
                if valid:
                    return valid
                return cards

        # Fallback: find all h4 elements that contain product links and walk up to parent containers
        h4_links = soup.select('h4 a[href]')
        if h4_links:
            cards = []
            for h4_a in h4_links:
                # Walk up to find a reasonable parent container
                parent = h4_a.parent  # h4
                if parent:
                    parent = parent.parent  # container div
                if parent:
                    cards.append(parent)
            if cards:
                return cards

        # Last resort: try h3 links
        h3_links = soup.select('h3 a[href]')
        if h3_links:
            cards = []
            for h3_a in h3_links:
                parent = h3_a.parent
                if parent:
                    parent = parent.parent
                if parent:
                    cards.append(parent)
            if cards:
                return cards

        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a product card from Proteini.si discount page.

        Price structure uses labels:
        - "AKCIJSKA CENA" followed by sale price (e.g., "99,00 RSD")
        - "REDOVNA CENA" followed by regular price (e.g., "189,00 RSD")
        """
        # Product name from h4 > a or h3 > a
        name = ""
        name_el = card.select_one('h4 a, h3 a, h2 a')
        if name_el:
            name = self._find_text(name_el)
        if not name:
            # Try any link with meaningful text
            for a in card.select('a[href]'):
                text = self._find_text(a)
                if text and len(text) > 3 and 'http' not in text:
                    name = text
                    break
        if not name:
            return None

        # Product URL from the same link
        product_url = ""
        link_el = card.select_one('h4 a[href], h3 a[href], h2 a[href]')
        if link_el:
            product_url = link_el.get('href', '')
        else:
            link_el = card.select_one('a[href]')
            if link_el:
                product_url = link_el.get('href', '')

        # Make URL absolute
        if product_url and not product_url.startswith('http'):
            product_url = self.BASE_URL + product_url

        # Image URL
        image_url = ""
        img = card.select_one('img')
        if img:
            for attr in ['data-src', 'data-lazy-src', 'src']:
                val = img.get(attr, '')
                if val:
                    if not val.startswith('http'):
                        val = self.BASE_URL + val
                    image_url = val
                    break

        # Prices: extract from text containing AKCIJSKA CENA and REDOVNA CENA
        card_text = card.get_text()
        original_price = None
        discount_price = None

        # Look for AKCIJSKA CENA (sale/action price) - this is the discounted price
        akcijska_match = re.search(
            r'AKCIJSKA\s+CENA\s*[:\s]*(\d[\d.,]*)\s*(?:RSD|rsd|din)?',
            card_text, re.IGNORECASE
        )
        if akcijska_match:
            discount_price = self.parse_price(akcijska_match.group(1))

        # Look for REDOVNA CENA (regular/original price)
        redovna_match = re.search(
            r'REDOVNA\s+CENA\s*[:\s]*(\d[\d.,]*)\s*(?:RSD|rsd|din)?',
            card_text, re.IGNORECASE
        )
        if redovna_match:
            original_price = self.parse_price(redovna_match.group(1))

        # If text-based extraction fails, try structured elements
        if not discount_price or not original_price:
            price_spans = card.select('span.price, .price, [class*="price"]')
            prices = []
            for span in price_spans:
                p = self.parse_price(self._find_text(span))
                if p and p > 0:
                    prices.append(p)
            if len(prices) >= 2:
                # Smaller price is discount, larger is original
                prices.sort()
                if not discount_price:
                    discount_price = prices[0]
                if not original_price:
                    original_price = prices[-1]
            elif len(prices) == 1 and not original_price:
                original_price = prices[0]

        # Extract discount percentage from badge if present
        # e.g. "-48%" badge
        discount_badge = re.search(r'-(\d+)%', card_text)

        # If we have original but not discount, compute from badge
        if original_price and not discount_price and discount_badge:
            pct = int(discount_badge.group(1))
            discount_price = round(original_price * (1 - pct / 100), 2)

        # If we have discount but not original, compute from badge
        if discount_price and not original_price and discount_badge:
            pct = int(discount_badge.group(1))
            if pct < 100:
                original_price = round(discount_price / (1 - pct / 100), 2)

        # Category - try to extract from card or URL
        category = ""
        cat_el = card.select_one('.category, .product-category')
        if cat_el:
            category = self._find_text(cat_el)

        return self.make_product(
            name=name,
            category=category or "Akcije",
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=True,
        )
