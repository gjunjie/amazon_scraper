"""
Performance monitoring and optimization utilities
"""
import time
import psutil
import threading
from typing import Dict, Any, List
from dataclasses import dataclass
from contextlib import contextmanager

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a scraping operation"""
    start_time: float
    end_time: float
    duration: float
    products_processed: int
    reviews_scraped: int
    memory_peak: float
    cpu_peak: float
    parallel_workers: int
    cache_hits: int
    cache_misses: int


class PerformanceMonitor:
    """Monitor and track performance metrics during scraping"""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.current_operation = None
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, operation_name: str, parallel_workers: int = 1):
        """Start monitoring performance for an operation"""
        self.current_operation = {
            'name': operation_name,
            'start_time': time.time(),
            'parallel_workers': parallel_workers,
            'products_processed': 0,
            'reviews_scraped': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_samples': [],
            'cpu_samples': []
        }
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        
        logger.info(f"📊 Started performance monitoring for {operation_name}")
    
    def stop_monitoring(self) -> PerformanceMetrics:
        """Stop monitoring and return metrics"""
        if not self.current_operation:
            return None
        
        end_time = time.time()
        duration = end_time - self.current_operation['start_time']
        
        # Calculate peak memory and CPU
        memory_peak = max(self.current_operation['memory_samples']) if self.current_operation['memory_samples'] else 0
        cpu_peak = max(self.current_operation['cpu_samples']) if self.current_operation['cpu_samples'] else 0
        
        metrics = PerformanceMetrics(
            start_time=self.current_operation['start_time'],
            end_time=end_time,
            duration=duration,
            products_processed=self.current_operation['products_processed'],
            reviews_scraped=self.current_operation['reviews_scraped'],
            memory_peak=memory_peak,
            cpu_peak=cpu_peak,
            parallel_workers=self.current_operation['parallel_workers'],
            cache_hits=self.current_operation['cache_hits'],
            cache_misses=self.current_operation['cache_misses']
        )
        
        self.metrics.append(metrics)
        self.monitoring = False
        self.current_operation = None
        
        logger.info(f"📊 Performance monitoring completed: {duration:.2f}s")
        return metrics
    
    def _monitor_resources(self):
        """Monitor system resources in background thread"""
        while self.monitoring and self.current_operation:
            try:
                # Get memory usage (MB)
                memory_mb = psutil.virtual_memory().used / 1024 / 1024
                self.current_operation['memory_samples'].append(memory_mb)
                
                # Get CPU usage (%)
                cpu_percent = psutil.cpu_percent()
                self.current_operation['cpu_samples'].append(cpu_percent)
                
                time.sleep(1)  # Sample every second
            except Exception as e:
                logger.debug(f"Error monitoring resources: {e}")
                break
    
    def update_products_processed(self, count: int):
        """Update products processed count"""
        if self.current_operation:
            self.current_operation['products_processed'] += count
    
    def update_reviews_scraped(self, count: int):
        """Update reviews scraped count"""
        if self.current_operation:
            self.current_operation['reviews_scraped'] += count
    
    def record_cache_hit(self):
        """Record a cache hit"""
        if self.current_operation:
            self.current_operation['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        if self.current_operation:
            self.current_operation['cache_misses'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary across all operations"""
        if not self.metrics:
            return {}
        
        total_duration = sum(m.duration for m in self.metrics)
        total_products = sum(m.products_processed for m in self.metrics)
        total_reviews = sum(m.reviews_scraped for m in self.metrics)
        total_cache_hits = sum(m.cache_hits for m in self.metrics)
        total_cache_misses = sum(m.cache_misses for m in self.metrics)
        
        avg_memory = sum(m.memory_peak for m in self.metrics) / len(self.metrics)
        avg_cpu = sum(m.cpu_peak for m in self.metrics) / len(self.metrics)
        
        return {
            'total_operations': len(self.metrics),
            'total_duration': total_duration,
            'total_products_processed': total_products,
            'total_reviews_scraped': total_reviews,
            'average_products_per_second': total_products / total_duration if total_duration > 0 else 0,
            'average_reviews_per_second': total_reviews / total_duration if total_duration > 0 else 0,
            'cache_hit_rate': total_cache_hits / (total_cache_hits + total_cache_misses) if (total_cache_hits + total_cache_misses) > 0 else 0,
            'average_memory_usage_mb': avg_memory,
            'average_cpu_usage_percent': avg_cpu,
            'parallel_efficiency': self._calculate_parallel_efficiency()
        }
    
    def _calculate_parallel_efficiency(self) -> float:
        """Calculate parallel processing efficiency"""
        if not self.metrics:
            return 0.0
        
        # Simple efficiency calculation based on workers vs performance
        total_workers = sum(m.parallel_workers for m in self.metrics)
        total_products = sum(m.products_processed for m in self.metrics)
        total_duration = sum(m.duration for m in self.metrics)
        
        if total_duration == 0 or total_workers == 0:
            return 0.0
        
        # Expected linear speedup vs actual speedup
        expected_rate = total_products / total_duration  # Single-threaded rate
        actual_rate = total_products / total_duration    # Actual rate
        
        # This is a simplified calculation - in practice, you'd want more sophisticated metrics
        return min(actual_rate / (expected_rate * total_workers), 1.0) if expected_rate > 0 else 0.0
    
    def log_performance_summary(self):
        """Log performance summary"""
        summary = self.get_performance_summary()
        if not summary:
            return
        
        logger.section("📊 PERFORMANCE SUMMARY", "=", 60)
        logger.info(f"Total operations: {summary['total_operations']}")
        logger.info(f"Total duration: {summary['total_duration']:.2f}s")
        logger.info(f"Products processed: {summary['total_products_processed']}")
        logger.info(f"Reviews scraped: {summary['total_reviews_scraped']}")
        logger.info(f"Products/second: {summary['average_products_per_second']:.2f}")
        logger.info(f"Reviews/second: {summary['average_reviews_per_second']:.2f}")
        logger.info(f"Cache hit rate: {summary['cache_hit_rate']:.1%}")
        logger.info(f"Avg memory usage: {summary['average_memory_usage_mb']:.1f} MB")
        logger.info(f"Avg CPU usage: {summary['average_cpu_usage_percent']:.1f}%")
        logger.info(f"Parallel efficiency: {summary['parallel_efficiency']:.1%}")
        logger.section("", "=", 60)


# Global performance monitor
performance_monitor = PerformanceMonitor()


@contextmanager
def monitor_performance(operation_name: str, parallel_workers: int = 1):
    """Context manager for performance monitoring"""
    performance_monitor.start_monitoring(operation_name, parallel_workers)
    try:
        yield performance_monitor
    finally:
        performance_monitor.stop_monitoring()


def get_system_info() -> Dict[str, Any]:
    """Get system information for performance analysis"""
    return {
        'cpu_count': psutil.cpu_count(),
        'memory_total_gb': psutil.virtual_memory().total / 1024 / 1024 / 1024,
        'memory_available_gb': psutil.virtual_memory().available / 1024 / 1024 / 1024,
        'disk_usage_percent': psutil.disk_usage('/').percent,
        'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}"
    }
