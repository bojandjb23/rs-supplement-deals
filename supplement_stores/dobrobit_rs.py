"""Scraper for dobrobit.rs - Health supplements store (Shopify platform)."""

import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup, Tag

from .base_store import BaseStoreScraper

logger = logging.getLogger(__name__)


class DobrobitScraper(BaseStoreScraper):
    STORE_NAME = "Dobrobit"
    BASE_URL = "https://dobrobit.rs"
    MAX_PAGES = 15

    # Shopify JSON API for the sale collection - much more reliable than HTML scraping
    SALE_JSON_URL = "/collections/akcije/products.json"

    def get_page_urls(self) -> List[str]:
        """Not used - we override scrape_all to use Shopify JSON API."""
        return []

    def get_product_cards(self, soup: BeautifulSoup) -> List[Tag]:
        """Not used - we override scrape_all to use Shopify JSON API."""
        return []

    def parse_product_card(self, card: Tag) -> Optional[Dict[str, Any]]:
        """Not used - we override scrape_all to use Shopify JSON API."""
        return None

    def scrape_all(self) -> List[Dict[str, Any]]:
        """Override to use Shopify JSON API instead of HTML scraping.

        The Shopify products.json endpoint returns structured data:
        {
            "products": [
                {
                    "title": "Product Name",
                    "handle": "url-slug",
                    "product_type": "Category",
                    "vendor": "Brand",
                    "variants": [
                        {
                            "price": "6950.00",
                            "compare_at_price": "7900.00",
                            "available": true
                        }
                    ],
                    "images": [{"src": "https://cdn.shopify.com/..."}]
                }
            ]
        }
        """
        self.products = []
        page = 1

        logger.info(f"[{self.STORE_NAME}] Scraping via Shopify JSON API...")

        while page <= self.MAX_PAGES:
            url = f"{self.BASE_URL}{self.SALE_JSON_URL}?page={page}"
            logger.debug(f"[{self.STORE_NAME}] Fetching page {page}: {url}")

            try:
                self._rate_limit()
                # Set Accept header to application/json for Shopify API
                headers = {"Accept": "application/json"}
                response = self.session.get(url, timeout=30, headers=headers)
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                logger.warning(f"[{self.STORE_NAME}] Failed to fetch page {page}: {e}")
                break

            products_data = data.get("products", [])
            if not products_data:
                # Empty page means we've reached the end
                logger.debug(f"[{self.STORE_NAME}] No products on page {page}, stopping.")
                break

            for product_json in products_data:
                parsed = self._parse_shopify_product(product_json)
                if parsed:
                    self.products.extend(parsed)

            logger.debug(
                f"[{self.STORE_NAME}] Page {page}: {len(products_data)} products found"
            )
            page += 1

        logger.info(f"[{self.STORE_NAME}] Scraped {len(self.products)} products total")
        return self.products

    def _parse_shopify_product(self, product: dict) -> List[Dict[str, Any]]:
        """Parse a single Shopify product JSON into one or more product dicts.

        Each variant with a compare_at_price > price becomes a separate product entry.
        If a product has no discounted variants, we still include it (it's in the sale
        collection for a reason).
        """
        results = []

        title = product.get("title", "").strip()
        if not title:
            return results

        handle = product.get("handle", "")
        product_url = f"{self.BASE_URL}/products/{handle}" if handle else ""
        product_type = product.get("product_type", "")
        vendor = product.get("vendor", "")

        # Get the first image
        images = product.get("images", [])
        image_url = images[0].get("src", "") if images else ""

        variants = product.get("variants", [])
        if not variants:
            return results

        # If there's only one variant, or all variants have the same price,
        # create a single product entry
        if len(variants) == 1 or self._all_same_price(variants):
            variant = variants[0]
            price = self._parse_shopify_price(variant.get("price"))
            compare_at = self._parse_shopify_price(variant.get("compare_at_price"))
            available = variant.get("available", True)

            # Determine original and discount prices
            original_price = None
            discount_price = None
            if compare_at and price and compare_at > price:
                original_price = compare_at
                discount_price = price
            elif price:
                original_price = price

            # Use variant-specific image if available
            variant_image = variant.get("featured_image", {})
            img = variant_image.get("src", "") if variant_image else ""
            if not img:
                img = image_url

            results.append(self.make_product(
                name=title,
                category=product_type or "Akcije",
                image_url=img,
                original_price=original_price,
                discount_price=discount_price,
                product_url=product_url,
                in_stock=available,
            ))
        else:
            # Multiple variants with different prices - create one entry per variant
            for variant in variants:
                variant_title = variant.get("title", "")
                full_name = f"{title} - {variant_title}" if variant_title and variant_title != "Default Title" else title

                price = self._parse_shopify_price(variant.get("price"))
                compare_at = self._parse_shopify_price(variant.get("compare_at_price"))
                available = variant.get("available", True)

                original_price = None
                discount_price = None
                if compare_at and price and compare_at > price:
                    original_price = compare_at
                    discount_price = price
                elif price:
                    original_price = price

                # Use variant-specific image if available
                variant_image = variant.get("featured_image", {})
                img = variant_image.get("src", "") if variant_image else ""
                if not img:
                    img = image_url

                results.append(self.make_product(
                    name=full_name,
                    category=product_type or "Akcije",
                    image_url=img,
                    original_price=original_price,
                    discount_price=discount_price,
                    product_url=product_url,
                    in_stock=available,
                ))

        return results

    @staticmethod
    def _parse_shopify_price(price_str) -> Optional[float]:
        """Parse Shopify price string (e.g., '6950.00') to float."""
        if not price_str:
            return None
        try:
            val = float(str(price_str))
            return val if val > 0 else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _all_same_price(variants: list) -> bool:
        """Check if all variants have the same price and compare_at_price."""
        if len(variants) <= 1:
            return True
        first_price = variants[0].get("price")
        first_compare = variants[0].get("compare_at_price")
        return all(
            v.get("price") == first_price and v.get("compare_at_price") == first_compare
            for v in variants
        )
