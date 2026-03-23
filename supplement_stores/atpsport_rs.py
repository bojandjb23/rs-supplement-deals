"""Scraper for atpsport.com - PrestaShop supplement store, official distributor of premium brands.

ATP Sport uses a standard PrestaShop setup. The /prices-drop page lists all discounted
products (currently ~7 items, all on one page).

Product card structure (PrestaShop):
  article.product-miniature[data-id-product, data-id-product-attribute]
    div.thumbnail-container
      div.thumbnail-container-image > a.thumbnail > img[src, data-full-size-image-url]
      div.product-description
        h3.product-title > a[href] -> product name + URL
        h3.product-title.product-availability-custom -> stock status
          span.product-message-availability-custom -> "Dostupno" / "Nije dostupno"
        div.product-price-and-shipping
          span.regular-price -> original price (e.g. "420 RSD")
          span.price -> discount price (e.g. "340 RSD")
      ul.product-flags
        li.on-sale -> "Akcija!"
        li.discount-percentage -> "- 80 RSD"
"""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class ATPSportScraper(BaseStoreScraper):
    STORE_NAME = "ATP Sport"
    BASE_URL = "https://www.atpsport.com"
    SALE_URL = "https://www.atpsport.com/prices-drop"

    def get_page_urls(self) -> List[str]:
        """Discover paginated URLs for /prices-drop.

        PrestaShop uses ?page=N for pagination. We check for next-page links.
        Currently all products fit on one page (~7 items).
        """
        soup = self.fetch_page(self.SALE_URL)
        if not soup:
            return [self.SALE_URL]

        max_page = 1

        # Look for pagination links with ?page=N
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            match = re.search(r"[?&]page=(\d+)", href)
            if match:
                max_page = max(max_page, int(match.group(1)))

        urls = []
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(self.SALE_URL)
            else:
                urls.append(f"{self.SALE_URL}?page={page}")
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract PrestaShop product cards - each is an article.product-miniature."""
        return soup.find_all("article", class_="product-miniature")

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a PrestaShop product card from the /prices-drop page.

        Structure:
            article.product-miniature
                div.thumbnail-container
                    a.thumbnail > img[src]
                    div.product-description
                        h3.product-title (not .product-availability-custom) > a -> name + URL
                        h3.product-availability-custom > span -> availability text
                        div.product-price-and-shipping
                            span.regular-price -> "420 RSD" (original)
                            span.price -> "340 RSD" (discounted)
                    ul.product-flags
                        li.on-sale -> "Akcija!"
                        li.discount-percentage -> "- 80 RSD"
        """
        # Product name and URL - use the h3.product-title that is NOT the availability one
        title_el = card.select_one("h3.product-title:not(.product-availability-custom) a")
        if not title_el:
            return None

        name = self._find_text(title_el)
        if not name:
            return None

        product_url = self._find_attr(title_el, "href")

        # Image URL
        img = card.select_one("a.thumbnail img")
        image_url = ""
        if img:
            image_url = img.get("data-full-size-image-url", "") or img.get("src", "")

        # Prices
        original_price = None
        discount_price = None

        regular_el = card.select_one("span.regular-price")
        sale_el = card.select_one("span.price")

        if regular_el:
            original_price = self.parse_price(self._find_text(regular_el))
        if sale_el:
            discount_price = self.parse_price(self._find_text(sale_el))

        # If no regular price but we have a sale price, treat as original
        if discount_price and not original_price:
            original_price = discount_price
            discount_price = None

        # Stock status
        avail_el = card.select_one("span.product-message-availability-custom")
        avail_text = self._find_text(avail_el).lower()
        in_stock = "dostupno" in avail_text if avail_text else True

        # Category from product URL path
        # e.g. /cokoladice-i-napici/1110-... -> "Cokoladice I Napici"
        category = "Akcija"
        if product_url:
            # Extract category slug from the URL path
            path = product_url.replace(self.BASE_URL, "").strip("/")
            parts = path.split("/")
            if len(parts) >= 2:
                cat_slug = parts[0]
                if cat_slug and not cat_slug[0].isdigit():
                    category = cat_slug.replace("-", " ").title()

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
