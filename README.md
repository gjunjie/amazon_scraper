# Amazon Scraper

A Python-based Amazon product and review scraper using Playwright for browser automation. This tool searches for products by keyword, extracts the top 3 product links, and scrapes user reviews with filtering and pagination support.

## Features

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

### Run with Visible Browser

View the browser during scraping (useful for debugging):
```bash
python amazon_scraper.py "laptop" --no-headless
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
2. **Search**: Searches Amazon for products matching the keyword
3. **Extract Products**: Retrieves the top 3 product links from search results
4. **Scrape Reviews**: For each product, navigates to the reviews page, applies star rating filter (if specified), and scrapes reviews with pagination
5. **Export**: Saves all data to JSON files in the `output/` directory

## Configuration

Edit `config.py` to customize:
- Rate limiting delays (MIN_DELAY, MAX_DELAY)
- Page load timeouts
- User agent strings
- Output directory

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

## Rate Limiting

The scraper includes built-in rate limiting:
- Random delays between 2-5 seconds (configurable in `config.py`)
- Respects page load times
- Should help avoid triggering Amazon's anti-bot measures

**Important**: Please use this tool responsibly and in accordance with Amazon's Terms of Service. Scraping may violate their terms, so use at your own risk.

## Project Structure

```
amazon_scraper/
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── .gitignore               # Git ignore rules
├── .env.example             # Environment variables template
├── config.py                # Configuration settings
├── amazon_scraper.py        # Main orchestrator
├── check_login.py           # Login status checker
├── utils/
│   ├── __init__.py
│   ├── login.py            # Login automation
│   ├── search.py           # Product search
│   └── reviews.py          # Review scraping
└── output/                 # Generated JSON files
```

## License

This project is provided as-is for educational purposes only.

## Disclaimer

This tool is for educational purposes only. Web scraping may violate Amazon's Terms of Service. Use at your own risk and responsibility.

