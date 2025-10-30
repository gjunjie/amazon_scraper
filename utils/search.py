"""
Product search module for Amazon
"""
import time
import random
import re
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import AMAZON_BASE_URL, MIN_DELAY, MAX_DELAY, PAGE_LOAD_TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)


class ProductSearch:
    """Handle product searches on Amazon"""
    
    def __init__(self, page: Page):
        """
        Initialize product search handler
        
        Args:
            page: Playwright page object
        """
        self.page = page
    
    def _random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
    
    def search_products(self, keyword: str, top_n: int = 3) -> list:
        """
        Search for products on Amazon and return top N product URLs
        
        Args:
            keyword: Search keyword
            top_n: Number of top products to return (default: 3)
            
        Returns:
            List of dictionaries with product information:
            [
                {
                    'rank': 1,
                    'title': 'Product Title',
                    'url': 'https://amazon.com/...',
                    'asin': 'B00XXXXXX'
                },
                ...
            ]
        """
        logger.browser_action("Starting product search", f"Keyword: '{keyword}', Target: {top_n} products")
        
        # Build search URL from base URL
        params = {'k': keyword}
        search_url = f"{AMAZON_BASE_URL}/s?{urlencode(params)}"
        
        try:
            # Navigate to search page
            logger.browser_action("Navigating to search page", search_url)
            # Use 'domcontentloaded' instead of 'networkidle' - more reliable
            self.page.goto(search_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            
            # Quick wait for page to stabilize - reduced from 2s to 0.5s
            logger.info("⏳ Waiting for page to stabilize...")
            time.sleep(0.5)
            try:
                self.page.wait_for_load_state('load', timeout=5000)  # Reduced timeout
            except Exception:
                pass  # Continue even if load state times out
            
            self._random_delay()
            
            # Wait for search results to load - try multiple selectors
            logger.info("🔍 Looking for search results...")
            result_selectors = [
                '[data-component-type="s-search-result"]',
                '[data-index]',  # Alternative selector for search results
                '.s-result-item',
                '.s-search-results .sg-col-inner'
            ]
            
            results_found = False
            for selector in result_selectors:
                try:
                    self.page.wait_for_selector(selector, timeout=10000)
                    logger.success(f"✅ Search results found using selector: {selector}")
                    results_found = True
                    break
                except PlaywrightTimeoutError:
                    logger.debug(f"Selector {selector} not found, trying next...")
                    continue
            
            if not results_found:
                # Take a screenshot for debugging
                screenshot_path = Path(__file__).parent.parent / "search_page_screenshot.png"
                self.page.screenshot(path=str(screenshot_path))
                logger.warning("⚠️ No search results found")
                logger.file_operation("saved", str(screenshot_path), "Debug screenshot")
                logger.browser_action("Current page info", f"URL: {self.page.url}, Title: {self.page.title()}")
                logger.error_with_solution(
                    "No search results found",
                    "Try a different keyword or check if Amazon is accessible"
                )
                return []
            
            # Quick wait for results to render - reduced from 2s to 0.5s
            logger.info("⏳ Waiting for results to render...")
            time.sleep(0.5)
            
            products = []
            
            # Find all search result items - try multiple selectors
            logger.info("🔍 Extracting search result items...")
            result_items = []
            result_selectors_try = [
                '[data-component-type="s-search-result"]',
                '[data-index][data-component-type="s-search-result"]',
            ]
            
            for selector in result_selectors_try:
                try:
                    # Wait for at least one element to be visible
                    try:
                        self.page.wait_for_selector(f"{selector}:visible", timeout=5000)
                    except Exception:
                        pass  # Continue even if visible check fails
                    
                    items = self.page.locator(selector).all()
                    if items and len(items) > 0:
                        result_items = items
                        logger.success(f"✅ Found {len(result_items)} search results using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Failed to find results with selector {selector}: {e}")
                    continue
            
            if not result_items:
                logger.warning("⚠️ No search result items found")
                # Take screenshot for debugging
                screenshot_path = Path(__file__).parent.parent / "search_results_screenshot.png"
                self.page.screenshot(path=str(screenshot_path))
                logger.file_operation("saved", str(screenshot_path), "Debug screenshot")
                logger.error_with_solution(
                    "No search result items found",
                    "Amazon may have changed their page structure or blocked the request"
                )
                return []
            
            # Iterate through all results to find first top_n non-sponsored products
            logger.info(f"🔄 Processing {len(result_items)} search results to find {top_n} products...")
            product_count = 0
            sponsored_count = 0
            no_href_count = 0
            
            for i, item in enumerate(result_items, 1):
                # Stop if we have enough non-sponsored products
                if len(products) >= top_n:
                    break
                
                # Show progress every 5 items
                if i % 5 == 0 or i == len(result_items):
                    logger.progress(i, len(result_items), f"Found {len(products)} products so far")
                
                try:
                    # Check if this item is sponsored and skip if so
                    is_sponsored = self._is_sponsored(item)
                    if is_sponsored:
                        sponsored_count += 1
                        logger.debug(f"Result {i} is sponsored, skipping")
                        continue
                    
                    # Try multiple selector strategies for the product link
                    href = None
                    title = None
                    
                    # Strategy 1: h2 a (most common)
                    try:
                        link_elements = item.locator('h2 a').all()
                        if link_elements and len(link_elements) > 0:
                            link_element = link_elements[0]
                            href = link_element.get_attribute('href', timeout=3000)
                            if href:
                                try:
                                    title = link_element.inner_text(timeout=3000).strip()
                                except:
                                    pass
                    except Exception as e1:
                        logger.debug(f"Strategy 1 (h2 a) failed for product {i}: {str(e1)[:100]}")
                    
                    # Strategy 2: Any anchor with href containing /dp/ or /gp/product/ (if Strategy 1 failed)
                    if not href:
                        try:
                            all_links = item.locator('a[href*="/dp/"], a[href*="/gp/product/"]').all()
                            if all_links:
                                link_element = all_links[0]
                                href = link_element.get_attribute('href', timeout=3000)
                                if href:
                                    try:
                                        title = link_element.inner_text(timeout=3000).strip()
                                    except:
                                        pass
                                    # If no title from link, try getting title from h2
                                    if not title:
                                        try:
                                            title = item.locator('h2').first.inner_text(timeout=3000).strip()
                                        except:
                                            pass
                        except Exception as e2:
                            logger.debug(f"Strategy 2 (product links) failed for product {i}: {str(e2)[:100]}")
                    
                    # Strategy 3: Try finding any link with a valid product URL pattern (if previous strategies failed)
                    if not href:
                        try:
                            # Get all links in the item and check for product URL patterns
                            all_links = item.locator('a').all()
                            for link in all_links:
                                try:
                                    potential_href = link.get_attribute('href', timeout=2000)
                                    if potential_href and ('/dp/' in potential_href or '/gp/product/' in potential_href):
                                        href = potential_href
                                        try:
                                            title = link.inner_text(timeout=2000).strip()
                                        except:
                                            pass
                                        break
                                except:
                                    continue
                        except Exception as e3:
                            logger.debug(f"Strategy 3 (any product link) failed for product {i}: {str(e3)[:100]}")
                    
                    # Strategy 4: Try h2 span a-link-normal (Amazon sometimes uses this)
                    if not href:
                        try:
                            link_element = item.locator('h2 span a-link-normal, h2.a-link-normal').first
                            href = link_element.get_attribute('href', timeout=3000)
                            if href:
                                try:
                                    title = link_element.inner_text(timeout=3000).strip()
                                except:
                                    pass
                        except:
                            pass
                    
                    if not href:
                        no_href_count += 1
                        logger.warning(f"No href found for result {i}, skipping")
                        continue
                    
                    # Build full URL if relative
                    if href.startswith('/'):
                        product_url = f"https://www.amazon.com{href}"
                    elif href.startswith('http'):
                        product_url = href
                    else:
                        product_url = f"https://www.amazon.com/{href}"
                    
                    # Extract ASIN from URL
                    asin = self._extract_asin(product_url)
                    
                    # If no title found, try to get it from the result item itself
                    if not title or not title.strip():
                        try:
                            title_selectors = ['h2', 'h2 span', '.a-text-normal', '[data-cy="title-recipe"]']
                            for title_selector in title_selectors:
                                try:
                                    title = item.locator(title_selector).first.inner_text(timeout=2000).strip()
                                    if title:
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        if not title or not title.strip():
                            title = f"Product {len(products) + 1}"  # Fallback title
                    
                    if product_url:
                        product_count += 1
                        products.append({
                            'rank': product_count,
                            'title': title or f"Product {product_count}",
                            'url': product_url,
                            'asin': asin
                        })
                        logger.info(f"Found product {product_count} (non-sponsored): {title[:50] if title else 'Unknown'}...")
                    else:
                        logger.warning(f"Incomplete data for result {i}")
                        
                except Exception as e:
                    logger.error(f"Error extracting product {i}: {e}", exc_info=True)
                    continue
            
            # Final summary
            logger.data_summary("Search results processed", len(result_items), 
                              f"{sponsored_count} sponsored, {no_href_count} no href, {len(products)} products extracted")
            
            if len(products) > 0:
                logger.success(f"✅ Successfully extracted {len(products)} products")
                for i, product in enumerate(products, 1):
                    logger.info(f"   {i}. {product['title'][:50]}... (ASIN: {product['asin']})")
            else:
                logger.warning("⚠️ No products extracted from search results")
                
            return products
            
        except PlaywrightTimeoutError:
            logger.error("⏰ Timeout waiting for search results")
            logger.error_with_solution(
                "Search timed out",
                "Try again with a different keyword or check your internet connection"
            )
            return []
        except Exception as e:
            logger.error(f"💥 Error during product search: {e}", exc_info=True)
            logger.error_with_solution(
                "Product search failed",
                "Check your internet connection and try again"
            )
            return []
    
    def _is_sponsored(self, item) -> bool:
        """
        Check if a search result item is sponsored
        
        Args:
            item: Playwright locator for a search result item
            
        Returns:
            True if the item is sponsored, False otherwise
        """
        try:
            # Check for sponsored in data attributes first (most reliable)
            try:
                component_type = item.get_attribute('data-component-type', timeout=1000)
                if component_type:
                    # Check if it's specifically a sponsored result
                    if component_type == 'sp-sponsored-result' or 'sp-sponsored' in component_type.lower():
                        return True
                    # If it's a regular search result, it's not sponsored
                    if component_type == 's-search-result':
                        # Still check for sponsored sub-type
                        component_sub_type = item.get_attribute('data-component-sub-type', timeout=500)
                        if component_sub_type and ('sp' in component_sub_type.lower() or 'ad' in component_sub_type.lower()):
                            return True
            except Exception:
                pass
            
            # Check for sponsored badge/indicator elements (specific selectors)
            sponsored_selectors = [
                '[data-component-type="sp-sponsored-result"]',
                '[data-component-sub-type="sp-ad-result"]',
                '.s-sponsored-label',
                '[class*="sponsored-label"]',
            ]
            
            for selector in sponsored_selectors:
                try:
                    sponsored_elems = item.locator(selector).all()
                    if sponsored_elems and len(sponsored_elems) > 0:
                        # Check if at least one is visible
                        for elem in sponsored_elems[:2]:  # Check first 2
                            try:
                                if elem.is_visible(timeout=500):
                                    return True
                            except:
                                continue
                except Exception:
                    continue
            
            # Check for "Sponsored" text but be more precise (avoid false positives)
            try:
                # Look for sponsored label text more specifically
                sponsored_selectors_text = [
                    'text="Sponsored"',
                    '.s-label-popover-default',
                    '[aria-label*="Sponsored"]',
                ]
                for text_selector in sponsored_selectors_text:
                    try:
                        sponsored_text_elems = item.locator(text_selector).all()
                        if sponsored_text_elems and len(sponsored_text_elems) > 0:
                            for elem in sponsored_text_elems[:2]:  # Check first 2 to avoid false positives
                                try:
                                    if elem.is_visible(timeout=500):
                                        return True
                                except:
                                    continue
                    except:
                        continue
            except Exception:
                pass
            
            return False
        except Exception as e:
            logger.debug(f"Error checking if item is sponsored: {e}")
            # When in doubt, don't filter it out
            return False
    
    def _extract_asin(self, url: str) -> str:
        """
        Extract ASIN from Amazon product URL
        
        Args:
            url: Product URL
            
        Returns:
            ASIN string or empty string
        """
        try:
            # ASIN is typically in the URL as /dp/ASIN or /product/ASIN
            patterns = [
                r'/dp/([A-Z0-9]{10})',
                r'/product/([A-Z0-9]{10})',
                r'/gp/product/([A-Z0-9]{10})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # Try to extract from query parameters
            if 'asin=' in url:
                asin_match = re.search(r'asin=([A-Z0-9]{10})', url)
                if asin_match:
                    return asin_match.group(1)
            
            return ''
        except Exception as e:
            logger.warning(f"Could not extract ASIN from URL {url}: {e}")
            return ''

