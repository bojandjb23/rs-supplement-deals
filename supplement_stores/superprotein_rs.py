"""Scraper for superprotein.rs - VirtueMart/Joomla supplement store from Nis.

"Snaga Prirode SHOP doo" operates this store with ~41 monthly deals across
three sale sections: /akcije, /akcija-2-1-gratis, and /kombo-akcije.

VirtueMart structure:
  div.product-container  (one per product)
    div.vm-product-media-container > a > img.browseProductImage
    div.vm-product-descr-container-0 > h2 > a  (product name + link)
    div.vm3pr-2 > div.product-price
      span.price-crossed  (sometimes empty)
      div.PricesalesPrice > span.PricesalesPrice  (discount/current price)
      div.PricepriceWithoutTax > span.PricepriceWithoutTax  (original/higher price)

Note: PricesalesPrice is the discounted price; PricepriceWithoutTax is the original
(pre-tax/full) price.  Some products only have PricesalesPrice with no original.
Products overlap between /akcije and /akcija-2-1-gratis - we deduplicate by URL.
"""

import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class SuperProteinScraper(BaseStoreScraper):
    STORE_NAME = "SuperProtein"
    BASE_URL = "https://www.superprotein.rs"

    SALE_URLS = [
        "https://www.superprotein.rs/prodavnica/akcije",
        "https://www.superprotein.rs/prodavnica/akcija-2-1-gratis",
        "https://www.superprotein.rs/prodavnica/kombo-akcije",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._seen_urls = set()

    def get_page_urls(self) -> List[str]:
        """Return all three sale section URLs. No pagination needed (all fit on one page each)."""
        return list(self.SALE_URLS)

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract VirtueMart product cards - each is a div.product-container."""
        return soup.find_all("div", class_="product-container")

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a SuperProtein VirtueMart product card.

        Structure:
            div.product-container
                div.vm-product-media-container > a[href, title] > img.browseProductImage[src]
                div.vm-product-descr-container-0 > h2 > a[href] -> product name
                div.vm3pr-2 > div.product-price
                    span.price-crossed (often empty)
                    div.PricesalesPrice > span.PricesalesPrice -> discount price
                    div.PricepriceWithoutTax > span.PricepriceWithoutTax -> original price
                div.vm-details-button > a.product-details
        """
        # Product name
        name_el = card.select_one("div.vm-product-descr-container-0 h2 a")
        name = self._find_text(name_el)
        if not name:
            return None

        # Product URL
        product_url = self._find_attr(name_el, "href")

        # Deduplicate across the three sale sections
        url_key = product_url.rstrip("/")
        if url_key in self._seen_urls:
            return None
        self._seen_urls.add(url_key)

        # Image URL
        img = card.select_one("img.browseProductImage")
        image_url = self._find_attr(img, "src") if img else ""

        # Prices
        original_price = None
        discount_price = None

        # PricesalesPrice = discounted/current price
        sales_price_el = card.select_one("span.PricesalesPrice")
        sales_price = self.parse_price(self._find_text(sales_price_el))

        # PricepriceWithoutTax = original/full price (higher value)
        original_price_el = card.select_one("span.PricepriceWithoutTax")
        full_price = self.parse_price(self._find_text(original_price_el))

        if sales_price and full_price and full_price > sales_price:
            # Standard case: sales price is lower, full price is the original
            discount_price = sales_price
            original_price = full_price
        elif sales_price:
            # Only sales price available - no discount info
            original_price = sales_price
            discount_price = None

        # Category - not available on sale listing pages
        category = "Akcija"

        # Stock - if product is listed on the sale page, assume in stock
        in_stock = True

        return self.make_product(
            name=name,
            category=category,
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )
