"""
Main Amazon scraper orchestrator
"""
import json
import logging
import sys
import argparse
from pathlib import Path

from utils.login import AmazonLogin
from utils.search import ProductSearch
from utils.reviews import ReviewScraper
from config import OUTPUT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


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
            'products': products
        }
        
        output_file = OUTPUT_DIR / 'products.json'
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(products)} products to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save products: {e}")
    
    def _save_reviews(self, product_asin: str, reviews_data: dict):
        """
        Save review data to JSON file
        
        Args:
            product_asin: Product ASIN for filename
            reviews_data: Review data dictionary
        """
        filename = f"reviews_{product_asin}.json" if product_asin else "reviews_unknown.json"
        output_file = OUTPUT_DIR / filename
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(reviews_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(reviews_data.get('reviews', []))} reviews to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save reviews: {e}")
    
    def scrape(self, keyword: str, star_rating: int = None, review_pages: int = 2):
        """
        Main scraping workflow
        
        Args:
            keyword: Search keyword
            star_rating: Filter reviews by star rating (1-5, optional)
            review_pages: Number of review pages to scrape per product
        """
        try:
            # Step 1: Initialize browser and login
            self._initialize_browser()
            
            # Step 2: Search for products
            logger.info(f"Starting scrape for keyword: '{keyword}'")
            search_handler = ProductSearch(self.page)
            products = search_handler.search_products(keyword, top_n=3)
            
            if not products:
                logger.warning("No products found")
                return
            
            # Save products
            self._save_products(keyword, products)
            
            # Step 3: Scrape reviews for each product
            review_scraper = ReviewScraper(self.page)
            
            for product in products:
                product_url = product['url']
                product_asin = product.get('asin', 'unknown')
                
                logger.info(f"Scraping reviews for product: {product['title'][:50]}...")
                
                try:
                    reviews_data = review_scraper.scrape_reviews(
                        product_url=product_url,
                        star_rating=star_rating,
                        max_pages=review_pages
                    )
                    
                    # Save reviews
                    self._save_reviews(product_asin, reviews_data)
                    
                except Exception as e:
                    logger.error(f"Error scraping reviews for product {product_asin}: {e}")
                    continue
            
            logger.info("Scraping completed successfully!")
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
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
    parser = argparse.ArgumentParser(description='Amazon Product and Review Scraper')
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
    
    scraper = AmazonScraper(headless=args.headless)
    
    try:
        scraper.scrape(
            keyword=args.keyword,
            star_rating=args.rating,
            review_pages=args.pages
        )
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        scraper.close()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        scraper.close()
        sys.exit(1)


if __name__ == '__main__':
    main()

