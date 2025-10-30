"""
Login automation module for Amazon using Playwright
"""
import json
import time
import logging
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from dotenv import load_dotenv

from config import COOKIES_FILE, AMAZON_BASE_URL, PAGE_LOAD_TIMEOUT, USER_AGENT

load_dotenv()

logger = logging.getLogger(__name__)


class AmazonLogin:
    """Handle Amazon login and cookie management"""
    
    def __init__(self, headless: bool = True):
        """
        Initialize Amazon login handler
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def _load_cookies(self) -> list:
        """
        Load cookies from file if they exist
        
        Returns:
            List of cookies or empty list
        """
        if COOKIES_FILE.exists():
            try:
                with open(COOKIES_FILE, 'r') as f:
                    cookies = json.load(f)
                    logger.info(f"Loaded {len(cookies)} cookies from file")
                    return cookies
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cookies: {e}")
                return []
        return []
    
    def _save_cookies(self, cookies: list):
        """
        Save cookies to file
        
        Args:
            cookies: List of cookie dictionaries
        """
        try:
            with open(COOKIES_FILE, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies to file")
        except IOError as e:
            logger.error(f"Failed to save cookies: {e}")
    
    def _check_cookies_valid(self, cookies: list) -> bool:
        """
        Check if saved cookies are still valid by attempting to use them
        
        Args:
            cookies: List of cookies to validate
            
        Returns:
            True if cookies are valid, False otherwise
        """
        if not cookies:
            return False
        
        try:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            self.context = self.browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            self.context.add_cookies(cookies)
            self.page = self.context.new_page()
            # Navigate to main Amazon page instead of sign-in page
            # If cookies are valid, we should stay on the main page
            # If invalid, Amazon will redirect us to sign-in
            self.page.goto(AMAZON_BASE_URL, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            time.sleep(3)
            
            # Check the current URL - if we were redirected to sign-in, cookies are invalid
            page_url = self.page.url.lower()
            if 'signin' in page_url or '/ap/' in page_url:
                logger.info("Cookies appear to be invalid (redirected to signin page)")
                return False
            
            # Use the proper is_logged_in method to verify login status
            # This is more reliable than checking individual UI elements
            try:
                is_logged_in = self.is_logged_in(self.page)
                if is_logged_in:
                    logger.info("Cookies appear to be valid (logged in verification passed)")
                    return True
                else:
                    logger.info("Cookies appear to be invalid (logged in verification failed)")
                    return False
            except Exception as e:
                logger.warning(f"Error during login verification: {e}")
                # If we're on main Amazon page and not redirected, cookies might be valid
                # But this is less reliable, so we're conservative
                if 'amazon.com' in page_url and 'signin' not in page_url and '/ap/' not in page_url:
                    logger.info("Cookies validation inconclusive, assuming invalid to be safe")
                return False
        except Exception as e:
            logger.warning(f"Error validating cookies: {e}")
            return False
    
    def login(self, email: str = None, password: str = None) -> BrowserContext:
        """
        Log in to Amazon and return browser context with cookies.
        This method uses manual login - it opens a browser pop-up window and waits for you to log in manually.
        Cookies are automatically saved for future use.
        
        Args:
            email: Ignored (kept for backwards compatibility)
            password: Ignored (kept for backwards compatibility)
            
        Returns:
            BrowserContext with logged-in session
        """
        # Check if cookies file exists (first-time vs subsequent login)
        is_first_time = not COOKIES_FILE.exists()
        
        # Try to load existing cookies first
        saved_cookies = self._load_cookies()
        if saved_cookies:
            # Check if cookies are valid (this will create a browser instance)
            if self._check_cookies_valid(saved_cookies):
                logger.info("✓ Using saved cookies - already logged in!")
                # Keep the context open and return it (context already initialized in _check_cookies_valid)
                return self.context
            else:
                logger.info("Saved cookies are expired or invalid. Manual login required.")
                # Cookies invalid, cleanup the browser instance created by _check_cookies_valid
                try:
                    if self.page:
                        self.page.close()
                    if self.context:
                        self.context.close()
                    if self.browser:
                        self.browser.close()
                    if self.playwright:
                        self.playwright.stop()
                except Exception:
                    pass
                # Reset state
                self.playwright = None
                self.browser = None
                self.context = None
                self.page = None
        
        # Need to perform manual login
        if is_first_time:
            logger.info("")
            logger.info("=" * 70)
            logger.info("  FIRST-TIME LOGIN - MANUAL AUTHENTICATION REQUIRED")
            logger.info("=" * 70)
            logger.info("  A browser window will pop up for you to log in to Amazon.")
            logger.info("  After you log in successfully, your cookies will be saved")
            logger.info("  automatically for future use (no need to log in again).")
            logger.info("=" * 70)
            logger.info("")
        else:
            logger.info("")
            logger.info("=" * 70)
            logger.info("  MANUAL LOGIN REQUIRED")
            logger.info("=" * 70)
            logger.info("  A browser window will pop up for you to log in to Amazon.")
            logger.info("  Your previous cookies expired or are invalid.")
            logger.info("  After you log in, new cookies will be saved for future use.")
            logger.info("=" * 70)
            logger.info("")
        
        try:
            # Always open browser in visible mode (pop-up window) for manual login
            # This ensures the browser is clearly visible to the user
            logger.info("Opening browser pop-up window...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=False)
            self.context = self.browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = self.context.new_page()
            
            # Navigate to Amazon base URL
            logger.info(f"Navigating to {AMAZON_BASE_URL}...")
            self.page.goto(AMAZON_BASE_URL, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
            
            # Wait for user to manually log in and close the window
            logger.info("")
            logger.info(">>> Browser window is now open. Please sign in to Amazon in that window. <<<")
            logger.info(">>> After signing in, close the browser window and press ENTER here to continue. <<<")
            logger.info("")
            
            # Wait for user to press Enter (simple and reliable)
            try:
                input("Press ENTER after you've signed in and closed the browser window: ")
                logger.info("User confirmed. Proceeding...")
            except (EOFError, KeyboardInterrupt):
                logger.info("Proceeding...")
            
            # Save cookies after window is closed
            logger.info("")
            logger.info("=" * 70)
            logger.info("  Saving cookies...")
            logger.info("=" * 70)
            try:
                cookies = self.context.cookies()
                if cookies:
                    self._save_cookies(cookies)
                    logger.info(f"  ✓ Successfully saved {len(cookies)} cookies to {COOKIES_FILE}")
                    logger.info("  ✓ You won't need to log in again on next run!")
                else:
                    logger.warning("  ⚠ No cookies found. You may need to log in again.")
                logger.info("=" * 70)
                logger.info("")
            except Exception as e:
                logger.error(f"Error saving cookies: {e}")
            
            return self.context
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            raise
    
    def is_logged_in(self, page: Page = None) -> bool:
        """
        Check if currently logged in to Amazon
        
        Args:
            page: Optional page object to check (uses self.page if not provided)
            
        Returns:
            True if logged in, False otherwise
        """
        page_to_check = page or self.page
        
        if not page_to_check:
            logger.warning("No page available to check login status")
            return False
        
        try:
            # Navigate to Amazon homepage if not already there
            current_url = page_to_check.url.lower()
            if 'amazon.com' not in current_url or 'signin' in current_url or '/ap/' in current_url:
                logger.info("Navigating to Amazon homepage to check login status...")
                page_to_check.goto(AMAZON_BASE_URL, wait_until='domcontentloaded', timeout=PAGE_LOAD_TIMEOUT)
                time.sleep(2)
            
            current_url = page_to_check.url.lower()
            
            # Check 1: URL check - if we're redirected to signin, not logged in
            if 'signin' in current_url or '/ap/' in current_url:
                logger.info("Login check: Redirected to signin page (NOT logged in)")
                return False
            
            # Check 2: Account menu indicator
            account_selectors = [
                '#nav-link-accountList',
                'id=nav-link-accountList',
                '[data-nav-role="signin"]'
            ]
            
            for selector in account_selectors:
                try:
                    account_element = page_to_check.locator(selector).first
                    if account_element.count() > 0:
                        text = account_element.inner_text(timeout=2000).lower()
                        
                        # If it says just "sign in" without "hello", likely not logged in
                        if 'sign in' in text and 'hello' not in text:
                            logger.info(f"Login check: Account menu shows '{text}' (NOT logged in)")
                            return False
                        
                        # If it has account info or shows "Hello, [Name]", likely logged in
                        if 'hello' in text or len(text.strip()) > 30:
                            logger.info(f"Login check: Account menu shows account info (LOGGED IN)")
                            return True
                        
                        # If text is just "Hello, sign in" or similar, check more indicators
                        if 'hello' in text and 'sign in' in text:
                            # This might mean not fully logged in - continue to other checks
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            # Check 3: Look for "Your Account" or "Orders" links (only visible when logged in)
            logged_in_indicators = [
                'a:has-text("Your Account")',
                '#nav-orders',
                'a:has-text("Returns")',
                'span:has-text("Account & Lists")'
            ]
            
            for indicator in logged_in_indicators:
                try:
                    element = page_to_check.locator(indicator).first
                    if element.count() > 0:
                        logger.info(f"Login check: Found logged-in indicator '{indicator}' (LOGGED IN)")
                        return True
                except Exception:
                    continue
            
            # Check 4: Try accessing account page to verify
            try:
                page_to_check.goto(f"{AMAZON_BASE_URL}/gp/css/homepage.html", wait_until='domcontentloaded', timeout=10000)
                time.sleep(2)
                
                if 'signin' in page_to_check.url.lower() or '/ap/' in page_to_check.url.lower():
                    logger.info("Login check: Redirected to signin when accessing account (NOT logged in)")
                    return False
                else:
                    logger.info("Login check: Can access account page (LOGGED IN)")
                    return True
            except Exception as e:
                logger.debug(f"Could not verify via account page: {e}")
            
            # Check 5: Look for "Sign in" button/link in navigation (if prominent, not logged in)
            try:
                signin_links = page_to_check.locator('a:has-text("Sign in"), button:has-text("Sign in")').filter(has_text="Sign in")
                if signin_links.count() > 2:  # Multiple sign-in links suggest not logged in
                    logger.info("Login check: Multiple sign-in links found (NOT logged in)")
                    return False
            except Exception:
                pass
            
            # Final check: If we're on main Amazon page and weren't redirected, likely logged in
            if 'amazon.com' in current_url and 'signin' not in current_url and '/ap/' not in current_url:
                logger.info("Login check: On main Amazon page without redirect (LOGGED IN - assumed)")
                return True
            
            logger.warning("Login check: Could not definitively determine login status")
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
    
    def close(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass  # Page may already be closed
        except Exception:
            pass
            
        try:
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass  # Context may already be closed
        except Exception:
            pass
            
        try:
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass  # Browser may already be closed
        except Exception:
            pass
            
        try:
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass  # Playwright may already be stopped
        except Exception:
            pass

