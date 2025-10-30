"""
Parallel processing utilities for Amazon scraper
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from config import USER_AGENT, PAGE_LOAD_TIMEOUT
from utils.logger import get_logger
from utils.reviews import ReviewScraper

logger = get_logger(__name__)


class ParallelReviewScraper:
    """Handle parallel review scraping for multiple products"""
    
    def __init__(self, max_workers: int = 3):
        """
        Initialize parallel review scraper
        
        Args:
            max_workers: Maximum number of parallel browser instances
        """
        self.max_workers = max_workers
        self.browser_instances = []
        self.contexts = []
        self.pages = []
    
    def _create_browser_instance(self) -> tuple[Browser, BrowserContext, Page]:
        """Create a new browser instance for parallel processing"""
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Don't load images for faster scraping
                '--disable-javascript',  # Disable JS for faster loading (if possible)
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-first-run',
                '--disable-logging',
                '--disable-permissions-api',
                '--disable-presentation-api',
                '--disable-print-preview',
                '--disable-speech-api',
                '--disable-file-system',
                '--disable-notifications',
                '--disable-geolocation',
                '--disable-media-session-api',
                '--disable-client-side-phishing-detection',
                '--disable-component-extensions-with-background-pages',
                '--disable-ipc-flooding-protection',
                '--aggressive-cache-discard',
                '--memory-pressure-off',
                '--max_old_space_size=4096',
            ]
        )
        
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            # Disable images and other resources for faster loading
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        )
        
        page = context.new_page()
        
        # Set faster timeouts
        page.set_default_timeout(PAGE_LOAD_TIMEOUT)
        
        return browser, context, page
    
    def _scrape_product_reviews(self, product_data: Dict[str, Any], star_rating: int = None, max_pages: int = 2) -> Dict[str, Any]:
        """
        Scrape reviews for a single product (runs in parallel worker)
        
        Args:
            product_data: Product information dictionary
            star_rating: Filter reviews by star rating
            max_pages: Maximum number of review pages to scrape
            
        Returns:
            Dictionary with review data and product info
        """
        browser = None
        context = None
        page = None
        
        try:
            # Create browser instance for this worker
            browser, context, page = self._create_browser_instance()
            
            # Create review scraper with this page
            review_scraper = ReviewScraper(page)
            
            # Scrape reviews
            reviews_data = review_scraper.scrape_reviews(
                product_url=product_data['url'],
                star_rating=star_rating,
                max_pages=max_pages
            )
            
            # Add product info to results
            result = {
                'product': product_data,
                'reviews_data': reviews_data,
                'success': True,
                'error': None
            }
            
            logger.info(f"✅ Successfully scraped {len(reviews_data.get('reviews', []))} reviews for {product_data.get('asin', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to scrape reviews for {product_data.get('asin', 'unknown')}: {e}")
            return {
                'product': product_data,
                'reviews_data': {'reviews': []},
                'success': False,
                'error': str(e)
            }
        finally:
            # Cleanup browser resources
            try:
                if page:
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()
            except Exception:
                pass
    
    def scrape_products_parallel(self, products: List[Dict[str, Any]], star_rating: int = None, max_pages: int = 2) -> List[Dict[str, Any]]:
        """
        Scrape reviews for multiple products in parallel
        
        Args:
            products: List of product dictionaries
            star_rating: Filter reviews by star rating
            max_pages: Maximum number of review pages to scrape per product
            
        Returns:
            List of results for each product
        """
        logger.info(f"🚀 Starting parallel review scraping for {len(products)} products with {self.max_workers} workers")
        
        results = []
        successful_products = 0
        total_reviews = 0
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_product = {
                executor.submit(self._scrape_product_reviews, product, star_rating, max_pages): product
                for product in products
            }
            
            # Process completed tasks
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['success']:
                        successful_products += 1
                        review_count = len(result['reviews_data'].get('reviews', []))
                        total_reviews += review_count
                        
                        logger.success(f"✅ Product {successful_products}/{len(products)}: {review_count} reviews")
                    else:
                        logger.warning(f"⚠️ Product failed: {product.get('asin', 'unknown')}")
                        
                except Exception as e:
                    logger.error(f"💥 Unexpected error processing product {product.get('asin', 'unknown')}: {e}")
                    results.append({
                        'product': product,
                        'reviews_data': {'reviews': []},
                        'success': False,
                        'error': str(e)
                    })
        
        # Summary
        logger.section("📊 PARALLEL SCRAPING SUMMARY", "=", 50)
        logger.data_summary("Products processed", successful_products, f"out of {len(products)} total")
        logger.data_summary("Total reviews scraped", total_reviews)
        logger.section("✅ PARALLEL SCRAPING COMPLETED!", "=", 50)
        
        return results


def scrape_reviews_parallel(products: List[Dict[str, Any]], star_rating: int = None, max_pages: int = 2, max_workers: int = 3) -> List[Dict[str, Any]]:
    """
    Convenience function for parallel review scraping
    
    Args:
        products: List of product dictionaries
        star_rating: Filter reviews by star rating
        max_pages: Maximum number of review pages to scrape per product
        max_workers: Maximum number of parallel workers
        
    Returns:
        List of results for each product
    """
    scraper = ParallelReviewScraper(max_workers=max_workers)
    return scraper.scrape_products_parallel(products, star_rating, max_pages)
