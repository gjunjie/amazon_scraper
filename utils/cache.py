"""
Caching utilities for Amazon scraper to avoid re-scraping same products
"""
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from config import OUTPUT_DIR
from utils.logger import get_logger

logger = get_logger(__name__)


class ScraperCache:
    """Intelligent caching system for scraper data"""
    
    def __init__(self, cache_dir: Path = None, cache_duration_hours: int = 24):
        """
        Initialize scraper cache
        
        Args:
            cache_dir: Directory to store cache files
            cache_duration_hours: How long to keep cached data (hours)
        """
        self.cache_dir = cache_dir or OUTPUT_DIR / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        self.cache_duration = timedelta(hours=cache_duration_hours)
        
        # Cache files
        self.products_cache_file = self.cache_dir / "products_cache.json"
        self.reviews_cache_file = self.cache_dir / "reviews_cache.json"
        
        # Load existing cache
        self.products_cache = self._load_cache(self.products_cache_file)
        self.reviews_cache = self._load_cache(self.reviews_cache_file)
    
    def _load_cache(self, cache_file: Path) -> Dict[str, Any]:
        """Load cache from file"""
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache from {cache_file}: {e}")
        return {}
    
    def _save_cache(self, cache_data: Dict[str, Any], cache_file: Path):
        """Save cache to file"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"Failed to save cache to {cache_file}: {e}")
    
    def _generate_cache_key(self, keyword: str, star_rating: Optional[int] = None) -> str:
        """Generate cache key for search parameters"""
        key_data = f"{keyword.lower().strip()}"
        if star_rating:
            key_data += f"_{star_rating}star"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if 'timestamp' not in cache_entry:
            return False
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cache_time < self.cache_duration
    
    def get_cached_products(self, keyword: str, star_rating: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached products for a search
        
        Args:
            keyword: Search keyword
            star_rating: Star rating filter
            
        Returns:
            Cached products list or None if not found/expired
        """
        cache_key = self._generate_cache_key(keyword, star_rating)
        
        if cache_key in self.products_cache:
            cache_entry = self.products_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.info(f"📦 Found cached products for '{keyword}' (expires in {self._get_cache_expiry_time(cache_entry)})")
                return cache_entry.get('products', [])
            else:
                logger.info(f"⏰ Cached products for '{keyword}' expired, will re-scrape")
                del self.products_cache[cache_key]
                self._save_cache(self.products_cache, self.products_cache_file)
        
        return None
    
    def cache_products(self, keyword: str, products: List[Dict[str, Any]], star_rating: Optional[int] = None):
        """
        Cache products for a search
        
        Args:
            keyword: Search keyword
            products: Products list to cache
            star_rating: Star rating filter
        """
        cache_key = self._generate_cache_key(keyword, star_rating)
        
        self.products_cache[cache_key] = {
            'keyword': keyword,
            'star_rating': star_rating,
            'products': products,
            'timestamp': datetime.now().isoformat(),
            'count': len(products)
        }
        
        self._save_cache(self.products_cache, self.products_cache_file)
        logger.info(f"💾 Cached {len(products)} products for '{keyword}'")
    
    def get_cached_reviews(self, product_asin: str, star_rating: Optional[int] = None, max_pages: int = 2) -> Optional[Dict[str, Any]]:
        """
        Get cached reviews for a product
        
        Args:
            product_asin: Product ASIN
            star_rating: Star rating filter
            max_pages: Number of pages scraped
            
        Returns:
            Cached reviews data or None if not found/expired
        """
        cache_key = f"{product_asin}_{star_rating or 'all'}_{max_pages}"
        
        if cache_key in self.reviews_cache:
            cache_entry = self.reviews_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.info(f"📝 Found cached reviews for {product_asin} ({len(cache_entry.get('reviews', []))} reviews)")
                return cache_entry.get('reviews_data', {})
            else:
                logger.info(f"⏰ Cached reviews for {product_asin} expired, will re-scrape")
                del self.reviews_cache[cache_key]
                self._save_cache(self.reviews_cache, self.reviews_cache_file)
        
        return None
    
    def cache_reviews(self, product_asin: str, reviews_data: Dict[str, Any], star_rating: Optional[int] = None, max_pages: int = 2):
        """
        Cache reviews for a product
        
        Args:
            product_asin: Product ASIN
            reviews_data: Reviews data to cache
            star_rating: Star rating filter
            max_pages: Number of pages scraped
        """
        cache_key = f"{product_asin}_{star_rating or 'all'}_{max_pages}"
        
        self.reviews_cache[cache_key] = {
            'asin': product_asin,
            'star_rating': star_rating,
            'max_pages': max_pages,
            'reviews_data': reviews_data,
            'timestamp': datetime.now().isoformat(),
            'review_count': len(reviews_data.get('reviews', []))
        }
        
        self._save_cache(self.reviews_cache, self.reviews_cache_file)
        logger.info(f"💾 Cached {len(reviews_data.get('reviews', []))} reviews for {product_asin}")
    
    def _get_cache_expiry_time(self, cache_entry: Dict[str, Any]) -> str:
        """Get human-readable cache expiry time"""
        if 'timestamp' not in cache_entry:
            return "unknown"
        
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        expiry_time = cache_time + self.cache_duration
        remaining = expiry_time - datetime.now()
        
        if remaining.total_seconds() <= 0:
            return "expired"
        
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def clear_expired_cache(self):
        """Remove expired cache entries"""
        expired_products = []
        expired_reviews = []
        
        # Check products cache
        for key, entry in self.products_cache.items():
            if not self._is_cache_valid(entry):
                expired_products.append(key)
        
        # Check reviews cache
        for key, entry in self.reviews_cache.items():
            if not self._is_cache_valid(entry):
                expired_reviews.append(key)
        
        # Remove expired entries
        for key in expired_products:
            del self.products_cache[key]
        
        for key in expired_reviews:
            del self.reviews_cache[key]
        
        if expired_products or expired_reviews:
            self._save_cache(self.products_cache, self.products_cache_file)
            self._save_cache(self.reviews_cache, self.reviews_cache_file)
            logger.info(f"🧹 Cleaned up {len(expired_products)} expired product entries and {len(expired_reviews)} expired review entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_products = sum(1 for entry in self.products_cache.values() if self._is_cache_valid(entry))
        valid_reviews = sum(1 for entry in self.reviews_cache.values() if self._is_cache_valid(entry))
        
        total_reviews = sum(len(entry.get('reviews_data', {}).get('reviews', [])) 
                          for entry in self.reviews_cache.values() 
                          if self._is_cache_valid(entry))
        
        return {
            'products_entries': len(self.products_cache),
            'valid_products_entries': valid_products,
            'reviews_entries': len(self.reviews_cache),
            'valid_reviews_entries': valid_reviews,
            'total_cached_reviews': total_reviews,
            'cache_duration_hours': self.cache_duration.total_seconds() / 3600
        }
    
    def clear_all_cache(self):
        """Clear all cache data"""
        self.products_cache.clear()
        self.reviews_cache.clear()
        
        # Remove cache files
        if self.products_cache_file.exists():
            self.products_cache_file.unlink()
        if self.reviews_cache_file.exists():
            self.reviews_cache_file.unlink()
        
        logger.info("🗑️ Cleared all cache data")


# Global cache instance
scraper_cache = ScraperCache()
