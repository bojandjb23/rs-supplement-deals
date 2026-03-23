"""Scraper for gymbeam.rs - Large multinational supplement e-commerce (Astro + Magento backend).

Products on the sale page (/rasprodaja) are rendered server-side as HTML product cards
inside a [data-test='cp-products'] container. Each card is an <a> tag with the product
link, image, name, discount badge, and current sale price.

Original prices are NOT shown in the HTML. The discount percentage is available in the
badge text (e.g., 'DO -30%' or 'POPUST -33%'). We compute the original price from the
sale price and discount percentage.

Pagination: ?p=2, ?p=3 etc. Page info from the astro-island props gives total_pages.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class GymBeamScraper(BaseStoreScraper):
    STORE_NAME = "GymBeam"
    BASE_URL = "https://www.gymbeam.rs"
    SALE_URL = "https://www.gymbeam.rs/rasprodaja"
    MAX_PAGES = 10

    def get_page_urls(self) -> List[str]:
        """Discover paginated URLs for the /rasprodaja sale page.

        Pagination uses ?p=N. Total pages is extracted from the astro-island
        props (page_info.total_pages) or by looking for pagination links.
        """
        soup = self.fetch_page(self.SALE_URL)
        if not soup:
            return [self.SALE_URL]

        max_page = 1

        # Method 1: Extract total_pages from astro-island props
        for island in soup.find_all("astro-island"):
            props = island.get("props", "")
            match = re.search(r'"total_pages":\[0,(\d+)\]', props)
            if match:
                max_page = max(max_page, int(match.group(1)))
                break

        # Method 2: Fallback to pagination links in HTML
        if max_page <= 1:
            for link in soup.find_all("a"):
                href = link.get("href", "")
                page_match = re.search(r"\?p=(\d+)", href)
                if page_match:
                    max_page = max(max_page, int(page_match.group(1)))

        max_page = min(max_page, self.MAX_PAGES)

        urls = []
        for page in range(1, max_page + 1):
            if page == 1:
                urls.append(self.SALE_URL)
            else:
                urls.append(f"{self.SALE_URL}?p={page}")
        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards from the [data-test='cp-products'] container.

        Each product card is a direct <a> child of the container div.
        """
        container = soup.find(attrs={"data-test": "cp-products"})
        if not container:
            return []
        return container.find_all("a", recursive=False)

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a GymBeam product card from the /rasprodaja page.

        Card structure (all inside an <a> tag):
          - href: full product URL
          - title: product name
          - img: product image (absolute URL)
          - Badge <p> with text like 'DO -30%' or 'POPUST -33%'
          - Price <span class='break-keep whitespace-nowrap'>: '1 500,00 RSD'
          - Product name <span class='product-name ...'>
        """
        # Product name from title attribute
        name = card.get("title", "").strip()
        if not name:
            name_span = card.find("span", class_=lambda c: c and "product-name" in c)
            if name_span:
                name = name_span.get_text(strip=True)
        if not name:
            return None

        # Product URL
        product_url = card.get("href", "")

        # Image
        img = card.find("img")
        image_url = ""
        if img:
            image_url = img.get("src", "") or img.get("data-src", "")

        # Discount percentage from badge
        discount_pct = 0
        # Look for the badge text containing a percentage
        for p_tag in card.find_all("p"):
            text = p_tag.get_text(strip=True)
            pct_match = re.search(r"-(\d+)%", text)
            if pct_match:
                discount_pct = int(pct_match.group(1))
                break

        # Sale price - the main price span
        # Structure: <span class="text-secondary mt-0.5 block font-bold md:text-lg">
        #   <span class="pr-1 ...">Od</span>
        #   <span class="break-keep whitespace-nowrap">1 500,00 RSD</span>
        # </span>
        discount_price = None
        original_price = None

        # Find the price span with class containing 'text-secondary' and 'font-bold'
        price_container = card.find(
            "span",
            class_=lambda c: c and "text-secondary" in c and "font-bold" in c,
        )
        if price_container:
            # Get the span with the actual price (has 'break-keep' and 'whitespace-nowrap')
            price_span = price_container.find(
                "span",
                class_=lambda c: c and "break-keep" in c and "whitespace-nowrap" in c
                and "text-xs" not in c and "font-normal" not in c,
            )
            if price_span:
                price_text = price_span.get_text(strip=True)
                discount_price = self.parse_price(price_text)

        # Compute original price from discount percentage
        if discount_price and discount_pct > 0:
            original_price = round(discount_price / (1 - discount_pct / 100), 2)
        elif discount_price:
            # No discount badge found - treat as regular price
            original_price = discount_price
            discount_price = None

        # Category from breadcrumbs in props or default to sale category
        category = "Rasprodaja"

        # Manufacturer/brand from the product name (often appended as "- BrandName")
        # Not extracting separately; included in name

        # Stock status - if it's listed, assume in stock
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
