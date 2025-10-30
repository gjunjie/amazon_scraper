"""
Enhanced logging utilities for Amazon scraper
"""
import logging
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        # Add color to the level name
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        # Add emoji based on level
        emoji_map = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
        
        if record.levelname.replace(self.COLORS.get(record.levelname, '') + record.levelname + self.COLORS['RESET'], record.levelname) in emoji_map:
            clean_level = record.levelname.replace(self.COLORS.get(record.levelname, '') + record.levelname + self.COLORS['RESET'], record.levelname)
            emoji = emoji_map[clean_level]
            record.levelname = f"{emoji} {record.levelname}"
        
        return super().format(record)


class ProgressTracker:
    """Track and display progress for operations"""
    
    def __init__(self, total: int, operation: str = "Processing"):
        self.total = total
        self.current = 0
        self.operation = operation
        self.start_time = time.time()
        self.last_update = 0
        
    def update(self, increment: int = 1, message: str = ""):
        """Update progress"""
        self.current += increment
        current_time = time.time()
        
        # Only update every 0.5 seconds to avoid spam
        if current_time - self.last_update < 0.5 and self.current < self.total:
            return
            
        self.last_update = current_time
        
        percentage = (self.current / self.total) * 100
        elapsed = current_time - self.start_time
        
        # Calculate ETA
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {eta:.1f}s" if eta > 0 else "ETA: <1s"
        else:
            eta_str = "ETA: calculating..."
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * self.current // self.total)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Format message
        status_msg = f"\r🔄 {self.operation}: [{bar}] {percentage:.1f}% ({self.current}/{self.total}) {eta_str}"
        if message:
            status_msg += f" - {message}"
        
        # Print without newline to update in place
        print(status_msg, end='', flush=True)
        
        if self.current >= self.total:
            print()  # New line when complete
            elapsed_total = time.time() - self.start_time
            print(f"✅ {self.operation} completed in {elapsed_total:.1f}s")


class ScraperLogger:
    """Enhanced logger for Amazon scraper with better formatting and utilities"""
    
    def __init__(self, name: str = "amazon_scraper", log_file: str = "scraper.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        colored_formatter = ColoredFormatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler (detailed)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler (colored)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(colored_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Performance tracking
        self.operation_times: Dict[str, float] = {}
        
    def start_operation(self, operation: str) -> str:
        """Start timing an operation"""
        operation_id = f"{operation}_{int(time.time() * 1000)}"
        self.operation_times[operation_id] = time.time()
        return operation_id
        
    def end_operation(self, operation_id: str, message: str = ""):
        """End timing an operation and log duration"""
        if operation_id in self.operation_times:
            duration = time.time() - self.operation_times[operation_id]
            del self.operation_times[operation_id]
            if message:
                self.info(f"⏱️ {message} completed in {duration:.2f}s")
            return duration
        return 0
        
    def info(self, message: str):
        """Log info message"""
        self.logger.info(message)
        
    def warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)
        
    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info)
        
    def debug(self, message: str):
        """Log debug message"""
        self.logger.debug(message)
        
    def success(self, message: str):
        """Log success message"""
        self.logger.info(f"✅ {message}")
        
    def step(self, step_num: int, total_steps: int, message: str):
        """Log a step in a multi-step process"""
        self.logger.info(f"📋 Step {step_num}/{total_steps}: {message}")
        
    def section(self, title: str, char: str = "=", width: int = 60):
        """Log a section header"""
        border = char * width
        self.logger.info("")
        self.logger.info(border)
        self.logger.info(f"  {title}")
        self.logger.info(border)
        self.logger.info("")
        
    def progress(self, current: int, total: int, message: str = ""):
        """Log progress"""
        percentage = (current / total) * 100
        bar_length = 20
        filled = int(bar_length * current // total)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        progress_msg = f"🔄 Progress: [{bar}] {percentage:.1f}% ({current}/{total})"
        if message:
            progress_msg += f" - {message}"
        self.logger.info(progress_msg)
        
    def data_summary(self, data_type: str, count: int, details: str = ""):
        """Log a data summary"""
        self.logger.info(f"📊 {data_type}: {count} items found")
        if details:
            self.logger.info(f"   Details: {details}")
            
    def performance_summary(self, operation: str, items_processed: int, duration: float):
        """Log performance summary"""
        rate = items_processed / duration if duration > 0 else 0
        self.logger.info(f"⚡ Performance: {operation} - {items_processed} items in {duration:.2f}s ({rate:.1f} items/s)")
        
    def error_with_solution(self, error: str, solution: str):
        """Log error with suggested solution"""
        self.logger.error(f"❌ Error: {error}")
        self.logger.info(f"💡 Solution: {solution}")
        
    def retry_attempt(self, attempt: int, max_attempts: int, operation: str):
        """Log retry attempt"""
        self.logger.warning(f"🔄 Retry {attempt}/{max_attempts}: {operation}")
        
    def browser_action(self, action: str, details: str = ""):
        """Log browser action"""
        self.logger.info(f"🌐 Browser: {action}")
        if details:
            self.logger.info(f"   {details}")
            
    def file_operation(self, operation: str, file_path: str, details: str = ""):
        """Log file operation"""
        self.logger.info(f"📁 File {operation}: {file_path}")
        if details:
            self.logger.info(f"   {details}")


# Global logger instance
scraper_logger = ScraperLogger()

# Convenience functions
def get_logger(name: str = None) -> ScraperLogger:
    """Get logger instance"""
    if name:
        return ScraperLogger(name)
    return scraper_logger

def log_performance(func):
    """Decorator to log function performance"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        operation_id = logger.start_operation(func.__name__)
        try:
            result = func(*args, **kwargs)
            logger.end_operation(operation_id, f"{func.__name__}")
            return result
        except Exception as e:
            logger.end_operation(operation_id, f"{func.__name__} (failed)")
            raise
    return wrapper
