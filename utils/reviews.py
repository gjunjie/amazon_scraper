"""
Review scraping module for Amazon products
"""
import time
import random
import re
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import MIN_DELAY, MAX_DELAY, PAGE_LOAD_TIMEOUT
from utils.logger import get_logger

logger = get_logger(__name__)


class ReviewScraper:
    """Handle review scraping from Amazon product pages"""
    
    def __init__(self, page: Page):
        """
        Initialize review scraper
        
        Args:
            page: Playwright page object
        """
        self.page = page
    
    def _random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
    
    def _get_reviews_url(self, product_url: str, star_rating: int = None) -> str:
        """
        Build reviews URL from product URL
        
        Args:
            product_url: Product detail page URL
            star_rating: Filter reviews by star rating (1-5, optional)
            
        Returns:
            Reviews page URL
        """
        # Extract ASIN from product URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', product_url) or \
                    re.search(r'/product/([A-Z0-9]{10})', product_url) or \
                    re.search(r'/gp/product/([A-Z0-9]{10})', product_url)
        
        if asin_match:
            asin = asin_match.group(1)
            reviews_url = f"https://www.amazon.com/product-reviews/{asin}"
        else:
            # Fallback: try to get from URL query params
            parsed = urlparse(product_url)
            query_params = parse_qs(parsed.query)
            if 'asin' in query_params:
                asin = query_params['asin'][0]
                reviews_url = f"https://www.amazon.com/product-reviews/{asin}"
            else:
                # Last resort: modify product URL
                reviews_url = product_url.replace('/dp/', '/product-reviews/')
        
        # Add star rating filter if specified
        if star_rating and 1 <= star_rating <= 5:
            parsed = urlparse(reviews_url)
            query_params = parse_qs(parsed.query)
            query_params['filterByStar'] = [f'five_star' if star_rating == 5 else 
                                           f'four_star' if star_rating == 4 else
                                           f'three_star' if star_rating == 3 else
                                           f'two_star' if star_rating == 2 else
                                           'one_star']
            query = urlencode(query_params, doseq=True)
            reviews_url = urlunparse(parsed._replace(query=query))
        
        return reviews_url
    
    def scrape_reviews(self, product_url: str, star_rating: int = None, max_pages: int = 2) -> dict:
        """
        Scrape reviews from a product page
        
        Args:
            product_url: Product detail page URL
            star_rating: Filter reviews by star rating (1-5, optional)
            max_pages: Maximum number of review pages to scrape (default: 2)
            
        Returns:
            Dictionary with review data:
            {
                'product_url': '...',
                'filter_rating': 5,
                'reviews': [...]
            }
        """
        reviews_url = self._get_reviews_url(product_url, star_rating)
        logger.browser_action("Starting review scraping", f"URL: {reviews_url}")
        if star_rating:
            logger.info(f"⭐ Filtering for {star_rating}-star reviews only")
        
        all_reviews = []
        page_num = 1
        
        try:
            # Navigate to reviews page
            logger.browser_action("Navigating to reviews page", reviews_url)
            self.page.goto(reviews_url, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            
            # Quick wait for initial page load - reduced timeout
            logger.info("⏳ Waiting for page to load...")
            try:
                self.page.wait_for_load_state('load', timeout=5000)  # Reduced from 10000
            except:
                pass
            
            # Check for "no reviews" case early
            logger.info("🔍 Checking for reviews availability...")
            page_content = self.page.content().lower()
            no_reviews_indicators = [
                'no customer reviews',
                'be the first to review',
                'no reviews yet',
                'this item has no reviews'
            ]
            
            if any(indicator in page_content for indicator in no_reviews_indicators):
                logger.warning("⚠️ No reviews found for this product")
                return {
                    'product_url': product_url,
                    'filter_rating': star_rating,
                    'reviews': []
                }
            
            # Wait for reviews container - use most reliable selector with reduced timeout
            logger.info("🔍 Looking for review elements...")
            try:
                self.page.wait_for_selector('[data-hook="review"]', timeout=5000, state='visible')  # Reduced from 10000
                logger.success("✅ Review elements found")
            except PlaywrightTimeoutError:
                # Check if there are truly no reviews
                if 'no customer reviews' in page_content or 'be the first to review' in page_content:
                    logger.warning("⚠️ No reviews found for this product")
                    return {
                        'product_url': product_url,
                        'filter_rating': star_rating,
                        'reviews': []
                    }
                logger.warning("⏰ Timeout waiting for reviews - attempting extraction anyway")
            
            # Extract reviews from pages
            logger.info(f"📄 Starting review extraction for {max_pages} pages...")
            while page_num <= max_pages:
                logger.info(f"📖 Scraping reviews from page {page_num}/{max_pages}...")
                
                page_reviews = self._extract_reviews_from_page()
                
                if not page_reviews:
                    if page_num == 1:
                        logger.warning("⚠️ No reviews found on first page - product may have no reviews")
                        break
                    else:
                        logger.info("ℹ️ No more reviews found")
                        break
                
                all_reviews.extend(page_reviews)
                logger.success(f"✅ Found {len(page_reviews)} reviews on page {page_num}")
                
                # Navigate to next page if available
                if page_num < max_pages:
                    logger.info("🔄 Checking for next page...")
                    if not self._navigate_to_next_page():
                        logger.info("ℹ️ No more pages available")
                        break
                    self._random_delay()
                
                page_num += 1
            
            logger.success(f"🎉 Total reviews scraped: {len(all_reviews)}")
            
            return {
                'product_url': product_url,
                'filter_rating': star_rating,
                'reviews': all_reviews
            }
            
        except Exception as e:
            logger.error(f"💥 Error scraping reviews: {e}", exc_info=True)
            logger.error_with_solution(
                "Review scraping failed",
                "Check if the product has reviews and try again"
            )
            return {
                'product_url': product_url,
                'filter_rating': star_rating,
                'reviews': all_reviews
            }
    
    def _extract_reviews_from_page(self) -> list:
        """
        Extract all reviews from the current page
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        
        try:
            # Quick scroll to trigger lazy loading (single scroll, no multiple passes) - reduced wait
            try:
                self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(0.2)  # Reduced from 0.5s
                self.page.evaluate("window.scrollTo(0, 0)")
            except:
                pass
            
            # Use primary selector (most reliable)
            review_elements = self.page.locator('[data-hook="review"]').all()
            
            if not review_elements:
                # Fallback to secondary selector
                review_elements = self.page.locator('[id*="customer_review"]').all()
            
            if not review_elements:
                logger.debug("No review elements found")
                return reviews
            
            logger.debug(f"Found {len(review_elements)} review elements to extract")
            
            # Extract reviews efficiently
            for review_element in review_elements:
                try:
                    review_data = {}
                    
                    # Extract reviewer nickname - try multiple selectors
                    reviewer_nickname = 'Anonymous'
                    nickname_selectors = [
                        '[data-hook="review-author"]',
                        '.a-profile-name',
                        '.a-profile-display-name',
                        '[class*="profile-name"]',
                        '[class*="reviewer-name"]',
                        '.a-text-bold',
                        'span.a-profile-name',
                        'div.a-profile-name',
                        'a[href*="/profile/"]',
                        'a[href*="/gp/profile/"]',
                        '.a-link-normal[href*="/profile/"]',
                        '[data-hook="review-author"] a',
                        '[data-hook="review-author"] span',
                        '.a-size-base.a-color-secondary',
                        '.a-size-mini.a-color-secondary'
                    ]
                    
                    for selector in nickname_selectors:
                        try:
                            nickname_elem = review_element.locator(selector).first
                            if nickname_elem.count() > 0:
                                text = nickname_elem.inner_text().strip()
                                # Filter out rating text and other unwanted content
                                if (text and 
                                    text.lower() not in ['', 'anonymous', 'amazon customer', 'verified purchase'] and
                                    not re.search(r'\d+\.?\d*\s*(?:out of|/)\s*5\s*stars?', text, re.IGNORECASE) and
                                    not re.search(r'^\d+\.?\d*\s*stars?$', text, re.IGNORECASE) and
                                    not re.search(r'^\d+\.?\d*$', text) and
                                    len(text) < 100):  # Avoid very long text that might be content
                                    reviewer_nickname = text
                                    break
                        except Exception:
                            continue
                    
                    # If still no nickname found, try getting text from the entire review author section
                    if reviewer_nickname == 'Anonymous':
                        try:
                            author_section = review_element.locator('[data-hook="review-author"], .a-profile-name, .a-profile-display-name').first
                            if author_section.count() > 0:
                                all_text = author_section.inner_text().strip()
                                # Split by common separators and take the first meaningful part
                                for separator in ['\n', '•', '|', 'on ']:
                                    if separator in all_text:
                                        potential_name = all_text.split(separator)[0].strip()
                                        # Apply same filtering as above
                                        if (potential_name and 
                                            potential_name.lower() not in ['', 'anonymous', 'amazon customer', 'verified purchase'] and
                                            not re.search(r'\d+\.?\d*\s*(?:out of|/)\s*5\s*stars?', potential_name, re.IGNORECASE) and
                                            not re.search(r'^\d+\.?\d*\s*stars?$', potential_name, re.IGNORECASE) and
                                            not re.search(r'^\d+\.?\d*$', potential_name) and
                                            len(potential_name) < 100):
                                            reviewer_nickname = potential_name
                                            break
                        except Exception:
                            pass
                    
                    review_data['reviewer_nickname'] = reviewer_nickname
                    
                    # Extract rating - try multiple selectors and methods
                    rating = 0
                    rating_selectors = [
                        '[data-hook="review-star-rating"]',
                        'i[data-hook="review-star-rating"]',
                        'i.a-icon-star',
                        '[aria-label*="out of 5"]',
                        '[aria-label*="stars"]',
                        '.a-icon-alt',
                        'span.a-icon-alt',
                        '[class*="a-star"]',
                        '.a-icon[class*="star"]'
                    ]
                    
                    for selector in rating_selectors:
                        try:
                            rating_elem = review_element.locator(selector).first
                            if rating_elem.count() > 0:
                                # Try aria-label first (most reliable)
                                aria_label = rating_elem.get_attribute('aria-label') or rating_elem.get_attribute('title') or ''
                                if aria_label:
                                    # Look for patterns like "5.0 out of 5 stars", "4 out of 5", etc.
                                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', aria_label, re.IGNORECASE)
                                    if not rating_match:
                                        rating_match = re.search(r'(\d+)', aria_label)
                                    if rating_match:
                                        potential_rating = float(rating_match.group(1))
                                        if 1 <= potential_rating <= 5:
                                            rating = int(potential_rating)
                                            break
                                
                                # Try text content
                                if rating == 0:
                                    text_content = rating_elem.inner_text() or ''
                                    if text_content:
                                        rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', text_content, re.IGNORECASE)
                                        if not rating_match:
                                            rating_match = re.search(r'(\d+)', text_content)
                                        if rating_match:
                                            potential_rating = float(rating_match.group(1))
                                            if 1 <= potential_rating <= 5:
                                                rating = int(potential_rating)
                                                break
                                
                                # Try class attribute for star rating classes
                                if rating == 0:
                                    class_attr = rating_elem.get_attribute('class') or ''
                                    if class_attr:
                                        if 'a-star-5' in class_attr or '5-star' in class_attr or 'a-star-5-' in class_attr:
                                            rating = 5
                                            break
                                        elif 'a-star-4' in class_attr or '4-star' in class_attr or 'a-star-4-' in class_attr:
                                            rating = 4
                                            break
                                        elif 'a-star-3' in class_attr or '3-star' in class_attr or 'a-star-3-' in class_attr:
                                            rating = 3
                                            break
                                        elif 'a-star-2' in class_attr or '2-star' in class_attr or 'a-star-2-' in class_attr:
                                            rating = 2
                                            break
                                        elif 'a-star-1' in class_attr or '1-star' in class_attr or 'a-star-1-' in class_attr:
                                            rating = 1
                                            break
                        except:
                            continue
                    
                    # Fallback: search within entire review element for star rating
                    if rating == 0:
                        try:
                            # Get all elements with aria-label containing rating
                            all_aria_elems = review_element.locator('[aria-label*="out of 5"], [aria-label*="stars"]').all()
                            for elem in all_aria_elems[:3]:  # Check first 3 matches
                                try:
                                    aria_label = elem.get_attribute('aria-label') or ''
                                    rating_match = re.search(r'(\d+\.?\d*)\s*(?:out of|/)\s*5', aria_label, re.IGNORECASE)
                                    if rating_match:
                                        potential_rating = float(rating_match.group(1))
                                        if 1 <= potential_rating <= 5:
                                            rating = int(potential_rating)
                                            break
                                except:
                                    continue
                        except:
                            pass
                    
                    review_data['rating'] = rating
                    
                    # Extract date (primary selector)
                    date_elem = review_element.locator('[data-hook="review-date"]').first
                    if date_elem.count() > 0:
                        review_data['date'] = date_elem.inner_text().strip()
                    else:
                        review_data['date'] = 'Unknown'
                    
                    # Extract review content (expand if needed, then get text)
                    try:
                        expand_btn = review_element.locator('[data-hook="expand-review"]').first
                        if expand_btn.count() > 0 and expand_btn.is_visible():
                            expand_btn.click()
                            time.sleep(0.05)  # Reduced from 0.1s
                    except:
                        pass
                    
                    content_elem = review_element.locator('[data-hook="review-body"] span').first
                    if content_elem.count() == 0:
                        content_elem = review_element.locator('[data-hook="review-body"]').first
                    
                    if content_elem.count() > 0:
                        content_text = content_elem.inner_text().strip()
                        review_data['content'] = content_text if len(content_text) > 10 else ''
                    else:
                        review_data['content'] = ''
                    
                    # Only add review if we have meaningful data
                    if review_data.get('content') or review_data.get('rating', 0) > 0:
                        reviews.append(review_data)
                        
                except Exception as e:
                    logger.debug(f"Error extracting review: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error extracting reviews: {e}")
        
        return reviews
    
    def _navigate_to_next_page(self) -> bool:
        """
        Navigate to the next page of reviews
        
        Returns:
            True if navigation successful, False otherwise
        """
        try:
            # Try multiple selectors for next button
            next_selectors = [
                'a[aria-label="Next Page"]',
                '[data-hook="pagination-next-link"]',
                '.a-pagination .a-last a',
                'a:has-text("Next")',
                '[aria-label*="Next"]'
            ]
            
            next_button = None
            for selector in next_selectors:
                locator = self.page.locator(selector).first
                if locator.count() > 0:
                    try:
                        # Check if button is visible and enabled
                        if locator.is_visible():
                            classes = locator.get_attribute('class') or ''
                            aria_disabled = locator.get_attribute('aria-disabled') or ''
                            if ('disabled' not in classes.lower() and 
                                'a-disabled' not in classes.lower() and
                                aria_disabled.lower() != 'true'):
                                next_button = locator
                                break
                    except:
                        continue
            
            if next_button:
                logger.debug("Clicking next page button...")
                next_button.click()
                
                # Wait for new page to load - reduced wait times
                time.sleep(1)  # Reduced from 2s
                try:
                    # Wait for reviews to load on new page
                    self.page.wait_for_selector('[data-hook="review"]', timeout=5000, state='visible')  # Reduced timeout
                except:
                    # Still wait a bit more if selector timeout
                    time.sleep(1)  # Reduced from 2s
                
                # Verify we're on a new page by checking URL changed or reviews reloaded
                review_count = self.page.locator('[data-hook="review"]').count()
                if review_count > 0:
                    logger.debug(f"Successfully navigated to next page, found {review_count} reviews")
                    return True
                else:
                    logger.debug("No reviews found after navigation")
                    return False
            
            logger.debug("No next page button found or it's disabled")
            return False
            
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False

