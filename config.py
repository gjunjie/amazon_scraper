"""
Configuration settings for Amazon scraper
"""
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Output directory
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Cookies file
COOKIES_FILE = BASE_DIR / "cookies.json"

# Rate limiting settings - Optimized for speed while avoiding detection
MIN_DELAY = 0.5  # Minimum delay between requests (seconds) - reduced from 2
MAX_DELAY = 1.5  # Maximum delay between requests (seconds) - reduced from 5
PAGE_LOAD_TIMEOUT = 15000  # Page load timeout in milliseconds - reduced from 30000

# User agent
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Amazon URLs
AMAZON_BASE_URL = "https://www.amazon.com"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds - reduced from 5

# Performance settings
ENABLE_CACHING = True  # Enable intelligent caching
CACHE_DURATION_HOURS = 24  # How long to keep cached data
DEFAULT_PARALLEL_WORKERS = 3  # Default number of parallel workers
MAX_PARALLEL_WORKERS = 10  # Maximum allowed parallel workers

# Browser optimization settings
DISABLE_IMAGES = True  # Don't load images for faster scraping
DISABLE_JAVASCRIPT = False  # Keep JS enabled for dynamic content
AGGRESSIVE_CACHE_DISCARD = True  # More aggressive memory management

