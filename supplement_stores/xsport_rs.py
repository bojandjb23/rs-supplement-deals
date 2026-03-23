"""Scraper for xsport.rs - Custom PHP supplement store."""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class XSportScraper(BaseStoreScraper):
    STORE_NAME = "X Sport"
    BASE_URL = "https://www.xsport.rs"

    SALE_URL = "/akcija"

    def get_page_urls(self) -> List[str]:
        """Discover paginated sale listing URLs."""
        first_url = f"{self.BASE_URL}{self.SALE_URL}"
        soup = self.fetch_page(first_url)
        if not soup:
            return [first_url]

        # Find max page from pagination links (?page=N)
        max_page = 1
        for link in soup.select("a[href*='page=']"):
            match = re.search(r"page=(\d+)", link.get("href", ""))
            if match:
                max_page = max(max_page, int(match.group(1)))

        urls = []
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(first_url)
            else:
                urls.append(f"{first_url}?page={page}")
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product card elements from the listing page."""
        selectors = [
            "div.product-list-item",
            "div.product-list > div",
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    @staticmethod
    def _parse_price_range(price_text: str):
        """Parse XSport price range format.

        Prices appear as "2240,00 - 2800,00 RSD" where the lower value is
        the discounted (sale) price and the higher value is the original price.
        Single prices (no range) are also handled.

        Returns:
            (original_price, discount_price) tuple of floats or Nones.
        """
        if not price_text:
            return None, None

        cleaned = price_text.strip()
        # Remove currency suffix
        cleaned = re.sub(r"\s*(RSD|Din|din|rsd)\s*\.?$", "", cleaned, flags=re.IGNORECASE).strip()

        # Split on dash separator (price range)
        parts = re.split(r"\s*[-–—]\s*", cleaned)

        if len(parts) == 2:
            # Range: "low - high" -> low is discount, high is original
            low_str = parts[0].strip()
            high_str = parts[1].strip()
            # Serbian format: comma as decimal, no thousands separator typically
            low = _serbian_price_to_float(low_str)
            high = _serbian_price_to_float(high_str)
            if low is not None and high is not None:
                if low < high:
                    return high, low  # (original, discount)
                elif high < low:
                    return low, high
                else:
                    return low, None  # same price, no discount
            return low or high, None
        elif len(parts) == 1:
            # Single price
            val = _serbian_price_to_float(parts[0].strip())
            return val, None
        return None, None

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a single product card from xsport.rs sale page."""
        # --- Product name ---
        name_el = card.select_one("a.product-list-title")
        if not name_el:
            # Fallback: find link to /proizvod/ with text
            for a in card.select("a[href*='/proizvod/']"):
                text = self._find_text(a)
                if text and len(text) > 2:
                    name_el = a
                    break
        name = self._find_text(name_el) if name_el else ""
        if not name:
            return None

        # --- Product URL ---
        product_url = ""
        for a in card.select("a[href*='/proizvod/']"):
            href = a.get("href", "")
            if href:
                product_url = href
                break
        if not product_url:
            link = card.select_one("a[href]")
            product_url = self._find_attr(link, "href")

        # --- Image URL ---
        image_url = ""
        img = card.select_one("img.img-responsive")
        if img:
            image_url = img.get("src", "")
        if not image_url:
            image_url = self._find_image_url(card)

        # --- Price ---
        price_el = card.select_one("span.price")
        price_text = self._find_text(price_el) if price_el else ""
        original_price, discount_price = self._parse_price_range(price_text)

        # --- Stock status ---
        in_stock = True
        card_text = card.get_text()
        if "Trenutno nema na lageru" in card_text:
            in_stock = False
        # Out-of-stock cards have btn-danger instead of btn-primary a2c
        if card.select_one("button.btn-danger") and not card.select_one("button.a2c"):
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


def _serbian_price_to_float(s: str) -> Optional[float]:
    """Convert a Serbian-formatted price string to float.

    Handles:
        "2240,00" -> 2240.0
        "2.240,00" -> 2240.0
        "2240" -> 2240.0
    """
    if not s:
        return None
    # Remove all whitespace
    s = s.strip()
    # Remove any remaining non-numeric chars except comma and dot
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None

    # Serbian: dot is thousands separator, comma is decimal
    last_comma = s.rfind(",")
    last_dot = s.rfind(".")

    if last_comma > -1 and last_dot > -1:
        if last_comma > last_dot:
            # "2.240,00" -> dot is thousands, comma is decimal
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif last_comma > -1:
        # Only comma: "2240,00" -> comma is decimal
        s = s.replace(",", ".")
    elif last_dot > -1:
        # Only dot: check if thousands separator
        parts_after = s.split(".")[-1]
        if len(parts_after) == 3:
            s = s.replace(".", "")
        # else keep as decimal

    try:
        return float(s)
    except ValueError:
        return None
