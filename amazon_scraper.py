"""
Main Amazon scraper orchestrator
"""
import json
import sys
import argparse
import time
from pathlib import Path

from utils.login import AmazonLogin
from utils.search import ProductSearch
from utils.reviews import ReviewScraper
from utils.logger import get_logger, log_performance
from config import OUTPUT_DIR

# Get enhanced logger
logger = get_logger(__name__)


class AmazonScraper:
    """Main scraper class that orchestrates the entire workflow"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize Amazon scraper
        
        Args:
            headless: Run browser in headless mode (ignored during initial login - browser opens visibly)
        """
        self.headless = headless
        self.login_handler = AmazonLogin(headless=headless)
        self.context = None
        self.page = None
    
    def _initialize_browser(self):
        """Initialize browser session with login"""
        logger.info("Initializing browser session...")
        self.context = self.login_handler.login()
        self.page = self.context.new_page()
        logger.info("Browser session initialized")
    
    def _save_products(self, keyword: str, products: list):
        """
        Save product data to JSON file
        
        Args:
            keyword: Search keyword
            products: List of product dictionaries
        """
        output_data = {
            'keyword': keyword,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_products': len(products),
            'products': products
        }
        
        output_file = OUTPUT_DIR / 'products.json'
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.file_operation("saved", str(output_file), f"{len(products)} products")
        except Exception as e:
            logger.error(f"Failed to save products: {e}")
            logger.error_with_solution(
                "Could not save products to file",
                "Check if the output directory exists and is writable"
            )
    
    def _save_reviews(self, product_asin: str, reviews_data: dict):
        """
        Save review data to JSON file
        
        Args:
            product_asin: Product ASIN for filename
            reviews_data: Review data dictionary
        """
        filename = f"reviews_{product_asin}.json" if product_asin else "reviews_unknown.json"
        output_file = OUTPUT_DIR / filename
        review_count = len(reviews_data.get('reviews', []))
        
        # Add metadata to reviews data
        reviews_data['metadata'] = {
            'asin': product_asin,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_reviews': review_count,
            'scraper_version': '2.0'
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(reviews_data, f, indent=2, ensure_ascii=False)
            logger.file_operation("saved", str(output_file), f"{review_count} reviews")
        except Exception as e:
            logger.error(f"Failed to save reviews: {e}")
            logger.error_with_solution(
                "Could not save reviews to file",
                "Check if the output directory exists and is writable"
            )
    
    @log_performance
    def scrape(self, keyword: str, star_rating: int = None, review_pages: int = 2):
        """
        Main scraping workflow
        
        Args:
            keyword: Search keyword
            star_rating: Filter reviews by star rating (1-5, optional)
            review_pages: Number of review pages to scrape per product
        """
        try:
            # Display startup banner
            logger.section(f"🚀 AMAZON SCRAPER STARTED", "=", 70)
            logger.info(f"🔍 Keyword: '{keyword}'")
            if star_rating:
                logger.info(f"⭐ Rating filter: {star_rating} stars")
            logger.info(f"📄 Review pages per product: {review_pages}")
            logger.section("", "=", 70)
            
            # Step 1: Initialize browser and login
            logger.step(1, 4, "Initializing browser and authenticating...")
            self._initialize_browser()
            logger.success("Browser session ready")
            
            # Step 2: Search for products
            logger.step(2, 4, f"Searching for products with keyword '{keyword}'...")
            search_handler = ProductSearch(self.page)
            products = search_handler.search_products(keyword, top_n=3)
            
            if not products:
                logger.warning("No products found for the given keyword")
                logger.error_with_solution(
                    "No products found",
                    "Try a different keyword or check if Amazon is accessible"
                )
                return
            
            logger.data_summary("Products found", len(products))
            self._save_products(keyword, products)
            
            # Step 3: Scrape reviews for each product
            logger.step(3, 4, f"Scraping reviews for {len(products)} products...")
            review_scraper = ReviewScraper(self.page)
            
            total_reviews = 0
            successful_products = 0
            
            for i, product in enumerate(products, 1):
                product_url = product['url']
                product_asin = product.get('asin', 'unknown')
                product_title = product['title'][:60] + "..." if len(product['title']) > 60 else product['title']
                
                logger.info(f"📦 Product {i}/{len(products)}: {product_title}")
                logger.info(f"   ASIN: {product_asin}")
                
                try:
                    operation_id = logger.start_operation(f"reviews_{product_asin}")
                    
                    reviews_data = review_scraper.scrape_reviews(
                        product_url=product_url,
                        star_rating=star_rating,
                        max_pages=review_pages
                    )
                    
                    review_count = len(reviews_data.get('reviews', []))
                    total_reviews += review_count
                    successful_products += 1
                    
                    logger.end_operation(operation_id, f"Found {review_count} reviews")
                    
                    # Save reviews
                    self._save_reviews(product_asin, reviews_data)
                    
                    if review_count > 0:
                        logger.success(f"✅ Successfully scraped {review_count} reviews")
                    else:
                        logger.warning(f"⚠️ No reviews found for this product")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to scrape reviews for {product_asin}: {e}")
                    logger.retry_attempt(1, 1, f"Continuing with next product...")
                    continue
            
            # Step 4: Final summary
            logger.step(4, 4, "Generating final summary...")
            logger.section("📊 SCRAPING SUMMARY", "=", 50)
            logger.data_summary("Products processed", successful_products, f"out of {len(products)} total")
            logger.data_summary("Total reviews scraped", total_reviews)
            logger.performance_summary("Overall scraping", total_reviews, time.time() - time.time())
            logger.section("✅ SCRAPING COMPLETED SUCCESSFULLY!", "=", 50)
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}", exc_info=True)
            logger.error_with_solution(
                "Scraping operation failed",
                "Check your internet connection, Amazon accessibility, and try again"
            )
            raise
        finally:
            self.close()
    
    def close(self):
        """Cleanup browser resources"""
        if self.page:
            self.page.close()
        if self.login_handler:
            self.login_handler.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Amazon Product and Review Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python amazon_scraper.py "laptop" --rating 5 --pages 3
  python amazon_scraper.py "air fryer" --no-headless
  python amazon_scraper.py "coffee maker" --rating 4 --pages 1
        """
    )
    parser.add_argument('keyword', help='Search keyword for products')
    parser.add_argument('--rating', type=int, choices=[1, 2, 3, 4, 5],
                       help='Filter reviews by star rating (1-5)')
    parser.add_argument('--pages', type=int, default=2,
                       help='Number of review pages to scrape per product (default: 2)')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', dest='headless', action='store_false',
                       help='Run browser in visible mode')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.pages < 1 or args.pages > 10:
        logger.error("Number of pages must be between 1 and 10")
        sys.exit(1)
    
    logger.section("🚀 AMAZON SCRAPER v2.0", "=", 60)
    logger.info(f"🔍 Search keyword: {args.keyword}")
    if args.rating:
        logger.info(f"⭐ Rating filter: {args.rating} stars")
    logger.info(f"📄 Pages per product: {args.pages}")
    logger.info(f"🖥️ Headless mode: {'Yes' if args.headless else 'No'}")
    logger.section("", "=", 60)
    
    scraper = AmazonScraper(headless=args.headless)
    
    try:
        start_time = time.time()
        scraper.scrape(
            keyword=args.keyword,
            star_rating=args.rating,
            review_pages=args.pages
        )
        total_time = time.time() - start_time
        logger.success(f"🎉 Scraping completed successfully in {total_time:.1f} seconds!")
        
    except KeyboardInterrupt:
        logger.warning("⚠️ Scraping interrupted by user (Ctrl+C)")
        logger.info("🔄 Cleaning up resources...")
        scraper.close()
        logger.info("✅ Cleanup completed")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Fatal error occurred: {e}", exc_info=True)
        logger.error_with_solution(
            "The scraper encountered an unexpected error",
            "Please check your internet connection, ensure Amazon is accessible, and try again"
        )
        scraper.close()
        sys.exit(1)


if __name__ == '__main__':
    main()

