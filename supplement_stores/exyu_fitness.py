"""Scraper for exyu-fitness.rs - CS-Cart supplement store, 20+ year veteran."""

import re
import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class ExYuFitnessScraper(BaseStoreScraper):
    STORE_NAME = "ExYu Fitness"
    BASE_URL = "https://www.exyu-fitness.rs"
    MAX_PAGES = 20

    # Two sale sections on this store
    SALE_URLS = [
        "/rasprodaja-suplementi/",
        "/suplementi-kratak-rok/",
    ]

    def get_page_urls(self) -> List[str]:
        """Discover paginated URLs for both sale sections.

        CS-Cart uses ?page=N query parameter for pagination.
        """
        urls = []

        for sale_path in self.SALE_URLS:
            first_url = f"{self.BASE_URL}{sale_path}"
            soup = self.fetch_page(first_url)
            if not soup:
                urls.append(first_url)
                continue

            # Find max page from pagination links
            max_page = 1

            # CS-Cart pagination links contain ?page=N
            for link in soup.select('a[href*="page="]'):
                href = link.get('href', '')
                match = re.search(r'[?&]page=(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

            # Also check text-based page numbers
            for link in soup.select('.ty-pagination__item a, .pagination a'):
                text = link.get_text(strip=True)
                if text.isdigit():
                    max_page = max(max_page, int(text))

            max_page = min(max_page, self.MAX_PAGES)
            for page in range(1, max_page + 1):
                if page == 1:
                    urls.append(first_url)
                else:
                    urls.append(f"{first_url}?page={page}")

        return urls

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Extract product cards from CS-Cart listing.

        CS-Cart uses .ut2-gl__item for grid layout items.
        """
        selectors = [
            '.ut2-gl__item',
            '.ty-column4',
            '.ty-column3',
            '.ty-grid-list__item',
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                return cards
        return []

    def _category_from_url(self, url: str) -> str:
        """Determine category based on which sale section the URL belongs to."""
        if 'suplementi-kratak-rok' in url:
            return "Kratak rok"
        elif 'rasprodaja' in url:
            return "Rasprodaja"
        return "Akcije"

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Parse a CS-Cart product card.

        Actual HTML structure:
        <div class="ut2-gl__item ...">
          <a class="product-title" href="...">Product Name</a>
          <img class="ty-pict" src="..." alt="...">
          <span class="ty-price">5.500rsd</span>           (sale price)
          <span class="ty-list-price">6.990rsd</span>      (original price)
          <span class="ty-list-price ty-save-price">-21%</span>
        </div>
        """
        # Product name: CS-Cart uses .ut2-gl__name a or a.product-title
        name = ""
        name_el = card.select_one('.ut2-gl__name a, a.product-title')
        if name_el:
            name = self._find_text(name_el)

        # Fallback: text-bearing link that is not an image wrapper
        if not name:
            for a in card.select('a[href]'):
                text = self._find_text(a)
                if text and len(text) > 3 and not a.select_one('img'):
                    name = text
                    break

        # Last fallback: img alt text
        if not name:
            img = card.select_one('img[alt]')
            if img and img.get('alt'):
                name = img.get('alt', '').strip()

        if not name:
            return None

        # Product URL
        product_url = ""
        url_el = card.select_one('.ut2-gl__name a, a.product-title')
        if url_el:
            product_url = url_el.get('href', '')
        if not product_url:
            for a in card.select('a[href]'):
                href = a.get('href', '')
                if href and '/suplementi/' in href:
                    product_url = href
                    break

        # Image URL
        image_url = ""
        img = card.select_one('img.ty-pict, img')
        if img:
            for attr in ['data-src', 'data-lazy-src', 'src']:
                val = img.get(attr, '')
                if val and (val.startswith('http') or val.startswith('/')):
                    image_url = val
                    break

        # Prices: CS-Cart uses span.ty-price for sale price and
        # span.ty-list-price for original (strikethrough) price
        original_price = None
        discount_price = None

        # Sale price (current/discounted): span.ty-price contains "5.500rsd"
        sale_el = card.select_one('span.ty-price')
        if sale_el:
            # Get just the numeric part from ty-price-num if available
            num_el = sale_el.select_one('span.ty-price-num')
            if num_el:
                price_text = num_el.get_text(strip=True)
            else:
                price_text = sale_el.get_text(strip=True)
            discount_price = self.parse_price(price_text)

        # Original price (before discount): span.ty-list-price (not .ty-save-price)
        # There may be multiple .ty-list-price spans; we want the one with the actual price
        for lp in card.select('span.ty-list-price'):
            classes = lp.get('class', [])
            if 'ty-save-price' in classes:
                continue  # Skip the discount percentage span
            text = lp.get_text(strip=True)
            if text and any(c.isdigit() for c in text):
                original_price = self.parse_price(text)
                break

        # If only discount_price found, swap (it's actually the only/regular price)
        if discount_price and not original_price:
            original_price = discount_price
            discount_price = None

        # Stock status
        in_stock = True
        card_text = card.get_text()
        if 'Nema na lageru' in card_text or 'Nema na zalihama' in card_text:
            in_stock = False

        return self.make_product(
            name=name,
            category="",  # Will be set in scrape_all
            image_url=image_url,
            original_price=original_price,
            discount_price=discount_price,
            product_url=product_url,
            in_stock=in_stock,
        )

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Override to inject category based on sale section URL."""
        self.products = []
        urls = self.get_page_urls()
        if not urls:
            return self.products

        from tqdm import tqdm

        for url in tqdm(urls, desc=f"Scraping {self.STORE_NAME}", unit="page"):
            soup = self.fetch_page(url)
            if not soup:
                continue
            category = self._category_from_url(url)
            cards = self.get_product_cards(soup)
            for card in cards:
                try:
                    product = self.parse_product_card(card)
                    if product and product.get("name"):
                        if not product["category"] or product["category"] == "Ostalo":
                            product["category"] = category
                        self.products.append(product)
                except Exception as e:
                    logger.warning(f"[{self.STORE_NAME}] Parse error: {e}")

        logger.info(f"[{self.STORE_NAME}] Scraped {len(self.products)} products")
        return self.products
