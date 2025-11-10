"""
Performance monitoring and metrics for SnipVault.

Provides decorators and utilities for tracking operation performance,
identifying bottlenecks, and exporting metrics.
"""

import time
import functools
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
import json
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PerformanceMetric:
    """Record of a performance measurement."""

    timestamp: str
    operation: str
    duration_ms: float
    category: str  # db, api, search, embedding, etc.
    metadata: Dict[str, Any]
    status: str = "success"


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    SLOW_THRESHOLD_MS = {
        'db': 100,      # Database queries
        'api': 1000,    # API calls
        'search': 500,  # Search operations
        'embedding': 2000,  # Embedding generation
        'default': 500
    }

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize performance monitor.

        Args:
            storage_path: Path to metrics storage
        """
        self.storage_path = storage_path or (
            Path.home() / '.snipvault' / 'performance.jsonl'
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.session_metrics: List[PerformanceMetric] = []

    def record_metric(
        self,
        operation: str,
        duration_ms: float,
        category: str = 'default',
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success"
    ):
        """
        Record a performance metric.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            category: Metric category
            metadata: Additional metadata
            status: Operation status
        """
        metric = PerformanceMetric(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            duration_ms=duration_ms,
            category=category,
            metadata=metadata or {},
            status=status
        )

        self.session_metrics.append(metric)
        self._persist_metric(metric)

        # Log slow operations
        threshold = self.SLOW_THRESHOLD_MS.get(category, self.SLOW_THRESHOLD_MS['default'])
        if duration_ms > threshold:
            logger.warning(
                f"Slow {category} operation: {operation} took {duration_ms:.2f}ms "
                f"(threshold: {threshold}ms)"
            )

        logger.debug(f"Performance: {operation} - {duration_ms:.2f}ms")

    def _persist_metric(self, metric: PerformanceMetric):
        """
        Persist metric to storage.

        Args:
            metric: Metric to persist
        """
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(asdict(metric)) + '\n')
        except Exception as e:
            logger.error(f"Failed to persist metric: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session performance statistics.

        Returns:
            Dictionary with session stats
        """
        if not self.session_metrics:
            return {
                'total_operations': 0,
                'avg_duration_ms': 0.0,
                'max_duration_ms': 0.0,
                'min_duration_ms': 0.0,
                'by_category': {}
            }

        durations = [m.duration_ms for m in self.session_metrics]

        # Group by category
        by_category: Dict[str, Dict[str, Any]] = {}
        for metric in self.session_metrics:
            if metric.category not in by_category:
                by_category[metric.category] = {
                    'count': 0,
                    'total_ms': 0.0,
                    'avg_ms': 0.0,
                    'max_ms': 0.0,
                    'slow_count': 0
                }

            cat = by_category[metric.category]
            cat['count'] += 1
            cat['total_ms'] += metric.duration_ms
            cat['max_ms'] = max(cat['max_ms'], metric.duration_ms)

            threshold = self.SLOW_THRESHOLD_MS.get(metric.category, self.SLOW_THRESHOLD_MS['default'])
            if metric.duration_ms > threshold:
                cat['slow_count'] += 1

        # Calculate averages
        for cat_data in by_category.values():
            cat_data['avg_ms'] = cat_data['total_ms'] / cat_data['count']

        return {
            'total_operations': len(self.session_metrics),
            'avg_duration_ms': sum(durations) / len(durations),
            'max_duration_ms': max(durations),
            'min_duration_ms': min(durations),
            'by_category': by_category
        }

    def get_slow_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get slowest operations.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of slow operations
        """
        sorted_metrics = sorted(
            self.session_metrics,
            key=lambda m: m.duration_ms,
            reverse=True
        )

        return [
            {
                'operation': m.operation,
                'duration_ms': m.duration_ms,
                'category': m.category,
                'timestamp': m.timestamp
            }
            for m in sorted_metrics[:limit]
        ]

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        stats = self.get_session_stats()
        lines = []

        # Overall metrics
        lines.append('# HELP snipvault_operations_total Total number of operations')
        lines.append('# TYPE snipvault_operations_total counter')
        lines.append(f'snipvault_operations_total {stats["total_operations"]}')
        lines.append('')

        lines.append('# HELP snipvault_operation_duration_ms Operation duration in milliseconds')
        lines.append('# TYPE snipvault_operation_duration_ms gauge')
        lines.append(f'snipvault_operation_duration_ms{{stat="avg"}} {stats["avg_duration_ms"]:.2f}')
        lines.append(f'snipvault_operation_duration_ms{{stat="max"}} {stats["max_duration_ms"]:.2f}')
        lines.append(f'snipvault_operation_duration_ms{{stat="min"}} {stats["min_duration_ms"]:.2f}')
        lines.append('')

        # Per-category metrics
        lines.append('# HELP snipvault_category_operations_total Operations per category')
        lines.append('# TYPE snipvault_category_operations_total counter')
        for category, data in stats['by_category'].items():
            lines.append(f'snipvault_category_operations_total{{category="{category}"}} {data["count"]}')
        lines.append('')

        lines.append('# HELP snipvault_category_duration_avg_ms Average duration per category')
        lines.append('# TYPE snipvault_category_duration_avg_ms gauge')
        for category, data in stats['by_category'].items():
            lines.append(f'snipvault_category_duration_avg_ms{{category="{category}"}} {data["avg_ms"]:.2f}')

        return '\n'.join(lines)


# Global monitor instance
_monitor_instance: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get global performance monitor instance.

    Returns:
        PerformanceMonitor instance
    """
    global _monitor_instance

    if _monitor_instance is None:
        _monitor_instance = PerformanceMonitor()

    return _monitor_instance


def track_performance(category: str = 'default', operation_name: Optional[str] = None):
    """
    Decorator to track function performance.

    Args:
        category: Metric category
        operation_name: Custom operation name (defaults to function name)

    Usage:
        @track_performance(category='db')
        def query_database():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            op_name = operation_name or func.__name__
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                status = "error"
                raise

            finally:
                duration_ms = (time.time() - start_time) * 1000
                monitor.record_metric(
                    operation=op_name,
                    duration_ms=duration_ms,
                    category=category,
                    status=status,
                    metadata={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                )

        return wrapper
    return decorator


class PerformanceContext:
    """Context manager for tracking performance."""

    def __init__(self, operation: str, category: str = 'default', metadata: Optional[Dict] = None):
        """
        Initialize performance context.

        Args:
            operation: Operation name
            category: Metric category
            metadata: Additional metadata
        """
        self.operation = operation
        self.category = category
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.monitor = get_performance_monitor()

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Record metric."""
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            status = "success" if exc_type is None else "error"

            self.monitor.record_metric(
                operation=self.operation,
                duration_ms=duration_ms,
                category=self.category,
                metadata=self.metadata,
                status=status
            )


def track_operation(operation: str, category: str = 'default', metadata: Optional[Dict] = None):
    """
    Context manager for tracking operation performance.

    Args:
        operation: Operation name
        category: Metric category
        metadata: Additional metadata

    Usage:
        with track_operation('search_query', category='search'):
            results = search(query)
    """
    return PerformanceContext(operation, category, metadata)
