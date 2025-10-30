# Amazon Scraper v2.0 - High Performance Edition

A high-performance Python-based Amazon product and review scraper using Playwright for browser automation. This tool searches for products by keyword, extracts the top 3 product links, and scrapes user reviews with filtering, pagination, parallel processing, and intelligent caching.

## 🚀 Performance Features

- ⚡ **Parallel Processing**: Scrape multiple products simultaneously with configurable workers
- 💾 **Intelligent Caching**: Avoid re-scraping same products with smart cache management
- 🎯 **Optimized Delays**: Reduced wait times while maintaining reliability
- 🔧 **Browser Optimization**: Streamlined browser settings for maximum speed
- 📊 **Performance Monitoring**: Real-time performance metrics and system monitoring
- 🧹 **Cache Management**: Built-in cache statistics and cleanup tools

## Core Features

- 🔍 **Product Search**: Search Amazon by keyword and retrieve top 3 product detail page links
- ⭐ **Review Filtering**: Filter reviews by star rating (1-5 stars)
- 📄 **Pagination Support**: Scrape multiple pages of reviews (configurable)
- 🔐 **Manual Login**: Log in manually through a browser window, cookies are saved for future use
- 🛡️ **Rate Limiting**: Built-in delays and rate limiting to respect Amazon's servers
- 📊 **JSON Export**: Save products and reviews to structured JSON files

## Requirements

- Python 3.8 or higher
- Playwright browser binaries

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers:
```bash
playwright install chromium
```

4. **First-time login**: When you run the scraper for the first time, a browser window will open. Log in to Amazon manually in that window. Your cookies will be saved automatically for future use.

## Usage

### Basic Usage

Search for products and scrape all reviews:
```bash
python amazon_scraper.py "laptop"
```

### High-Performance Parallel Scraping

Use 5 parallel workers for maximum speed:
```bash
python amazon_scraper.py "laptop" --workers 5
```

### Filter Reviews by Star Rating

Only scrape 5-star reviews:
```bash
python amazon_scraper.py "laptop" --rating 5
```

Only scrape 4-star reviews:
```bash
python amazon_scraper.py "laptop" --rating 4
```

### Customize Review Pages

Scrape 3 pages of reviews per product:
```bash
python amazon_scraper.py "laptop" --pages 3
```

### Sequential Processing (Legacy Mode)

Disable parallel processing for compatibility:
```bash
python amazon_scraper.py "laptop" --no-parallel
```

### Run with Visible Browser

View the browser during scraping (useful for debugging):
```bash
python amazon_scraper.py "laptop" --no-headless
```

### Cache Management

View cache statistics:
```bash
python amazon_scraper.py --cache-stats
```

Clear all cached data:
```bash
python amazon_scraper.py --clear-cache
```

### Check Login Status

Verify if you're logged in to Amazon:
```bash
python check_login.py
```

Run in headless mode:
```bash
python check_login.py --headless
```

This script will:
- Load saved cookies if available
- Attempt to verify login status
- Show clear success/failure messages
- Help identify if you need to complete CAPTCHA or 2FA

### Command Line Options

```
positional arguments:
  keyword               Search keyword for products

optional arguments:
  --rating {1,2,3,4,5}  Filter reviews by star rating (1-5)
  --pages N            Number of review pages to scrape per product (default: 2)
  --headless           Run browser in headless mode (default)
  --no-headless        Run browser in visible mode
  --no-parallel        Disable parallel processing (use sequential scraping)
  --workers N          Number of parallel workers for review scraping (default: 3)
  --cache-stats        Show cache statistics and exit
  --clear-cache        Clear all cached data and exit
```

## Output

The scraper generates JSON files in the `output/` directory:

### Products File (`output/products.json`)
```json
{
  "keyword": "laptop",
  "products": [
    {
      "rank": 1,
      "title": "Product Title",
      "url": "https://www.amazon.com/dp/B00XXXXXX",
      "asin": "B00XXXXXX"
    }
  ]
}
```

### Reviews Files (`output/reviews_{ASIN}.json`)
```json
{
  "product_url": "https://www.amazon.com/dp/B00XXXXXX",
  "filter_rating": 5,
  "reviews": [
    {
      "reviewer_nickname": "John D.",
      "rating": 5,
      "date": "Reviewed in the United States on January 15, 2024",
      "content": "Great product! Highly recommended..."
    }
  ]
}
```

## How It Works

1. **Login**: On first run, a browser window opens for you to manually log in to Amazon. Cookies are automatically saved for future sessions. Subsequent runs use saved cookies if they're still valid.
2. **Search**: Searches Amazon for products matching the keyword (with intelligent caching)
3. **Extract Products**: Retrieves the top 3 product links from search results
4. **Parallel Review Scraping**: For each product, creates multiple browser instances to scrape reviews simultaneously with configurable workers
5. **Caching**: Intelligently caches products and reviews to avoid re-scraping
6. **Export**: Saves all data to JSON files in the `output/` directory

## Performance Optimizations

### Parallel Processing
- **Multiple Workers**: Scrape up to 10 products simultaneously
- **Independent Browser Instances**: Each worker gets its own browser context
- **Optimized Resource Usage**: Streamlined browser settings for maximum efficiency

### Intelligent Caching
- **Product Caching**: Avoid re-searching same keywords
- **Review Caching**: Skip re-scraping same products
- **Configurable Expiry**: Cache expires after 24 hours (configurable)
- **Cache Statistics**: Monitor cache hit rates and performance

### Browser Optimizations
- **Reduced Delays**: Optimized wait times (0.5-1.5s vs 2-5s)
- **Resource Blocking**: Disable images and unnecessary resources
- **Memory Management**: Aggressive cache discarding and memory optimization
- **Faster Timeouts**: Reduced page load timeouts for quicker failures

### Performance Monitoring
- **Real-time Metrics**: Track memory, CPU, and processing rates
- **Cache Analytics**: Monitor cache hit/miss ratios
- **Parallel Efficiency**: Measure parallel processing effectiveness
- **System Resources**: Monitor system performance during scraping

## Configuration

Edit `config.py` to customize:
- Rate limiting delays (MIN_DELAY, MAX_DELAY) - Optimized to 0.5-1.5s
- Page load timeouts - Reduced to 15s for faster failures
- User agent strings
- Output directory
- Parallel processing settings (DEFAULT_PARALLEL_WORKERS, MAX_PARALLEL_WORKERS)
- Caching settings (CACHE_DURATION_HOURS, ENABLE_CACHING)
- Browser optimization settings (DISABLE_IMAGES, AGGRESSIVE_CACHE_DISCARD)

## Troubleshooting

### Manual Login Required
When running for the first time or if cookies expire:
- A browser window will open automatically
- Log in to Amazon manually in the browser window
- The script will detect when you're logged in and save your cookies
- You have up to 5 minutes to complete the login process
- If you need more time, you can run the script again

### Login Fails
- Run `python check_login.py` to verify your login status
- If cookies are expired, delete `cookies.json` and run the scraper again to trigger manual login
- Complete CAPTCHA or 2FA if prompted during manual login
- The browser window will remain open until you complete the login or the timeout is reached

### No Reviews Found
- Some products may not have reviews
- The page structure might have changed (Amazon updates frequently)
- Check the logs in `scraper.log` for details

### Timeout Errors
- Increase `PAGE_LOAD_TIMEOUT` in `config.py`
- Check your internet connection
- Amazon might be rate-limiting you - increase delays in config

## Performance Tips

### Optimal Settings
- **Workers**: Use 3-5 workers for best performance (more may cause rate limiting)
- **Pages**: Limit to 2-3 pages per product for faster scraping
- **Caching**: Keep caching enabled for repeated searches
- **Memory**: Monitor memory usage with many workers

### Speed vs Reliability Trade-offs
- **More Workers**: Faster but higher memory usage and potential rate limiting
- **Fewer Pages**: Faster but fewer reviews per product
- **Caching**: Much faster for repeated searches but uses disk space
- **Reduced Delays**: Faster but higher chance of detection

## Rate Limiting

The scraper includes optimized rate limiting:
- Random delays between 0.5-1.5 seconds (reduced from 2-5s)
- Respects page load times
- Parallel processing with independent rate limiting per worker
- Intelligent caching to reduce unnecessary requests

**Important**: Please use this tool responsibly and in accordance with Amazon's Terms of Service. Scraping may violate their terms, so use at your own risk.

## Project Structure

```
amazon_scraper/
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── .env.example             # Environment variables template
├── config.py                # Configuration settings (optimized)
├── amazon_scraper.py        # Main orchestrator (with parallel processing)
├── check_login.py           # Login status checker
├── utils/
│   ├── __init__.py
│   ├── login.py            # Login automation
│   ├── search.py           # Product search (optimized)
│   ├── reviews.py          # Review scraping (optimized)
│   ├── parallel_scraper.py # Parallel processing utilities
│   ├── cache.py            # Intelligent caching system
│   ├── performance.py      # Performance monitoring
│   └── logger.py           # Enhanced logging
├── output/                 # Generated JSON files
│   └── cache/              # Cache storage directory
└── scraper.log             # Detailed operation logs
```

## License

This project is provided as-is for educational purposes only.

## Disclaimer

This tool is for educational purposes only. Web scraping may violate Amazon's Terms of Service. Use at your own risk and responsibility.

