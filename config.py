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

# Rate limiting settings
MIN_DELAY = 2  # Minimum delay between requests (seconds)
MAX_DELAY = 5  # Maximum delay between requests (seconds)
PAGE_LOAD_TIMEOUT = 30000  # Page load timeout in milliseconds

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
RETRY_DELAY = 5  # seconds

