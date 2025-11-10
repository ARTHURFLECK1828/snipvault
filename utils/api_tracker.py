"""
API usage tracking and cost monitoring for SnipVault.

Tracks API calls to Gemini, Pinecone, and other services
with cost estimation and usage reports.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class APICall:
    """Record of an API call."""

    timestamp: str
    service: str  # gemini, pinecone, openai, github
    operation: str  # embed, query, search, etc.
    tokens: int = 0
    items: int = 0
    duration_ms: float = 0.0
    status: str = "success"  # success, error
    cost_usd: float = 0.0


class APITracker:
    """Track API usage and estimate costs."""

    # Pricing per service (as of 2024, subject to change)
    PRICING = {
        'gemini': {
            'text-embedding-004': {'per_1k_chars': 0.0000125},  # $0.0000125 per 1K chars
            'gemini-2.5-flash': {'per_1k_chars': 0.000075},  # $0.000075 per 1K chars
        },
        'pinecone': {
            'query': {'per_1k': 0.0004},  # $0.40 per 1M queries
            'upsert': {'per_1k': 0.00002},  # $0.02 per 1M vectors
        },
        'openai': {
            'text-embedding-3-small': {'per_1k_tokens': 0.00002},  # $0.02 per 1M tokens
            'text-embedding-3-large': {'per_1k_tokens': 0.00013},  # $0.13 per 1M tokens
            'gpt-4o-mini': {'per_1k_tokens': 0.00015},  # $0.15 per 1M tokens (input)
        }
    }

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize API tracker.

        Args:
            storage_path: Path to storage file
        """
        self.storage_path = storage_path or (
            Path.home() / '.snipvault' / 'api_usage.jsonl'
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.session_calls: List[APICall] = []

    def track_call(
        self,
        service: str,
        operation: str,
        tokens: int = 0,
        items: int = 0,
        duration_ms: float = 0.0,
        status: str = "success",
        model: Optional[str] = None
    ):
        """
        Track an API call.

        Args:
            service: Service name (gemini, pinecone, openai)
            operation: Operation name (embed, query, etc.)
            tokens: Number of tokens/characters processed
            items: Number of items processed
            duration_ms: Duration in milliseconds
            status: Call status (success, error)
            model: Model name (if applicable)
        """
        cost = self._estimate_cost(service, operation, tokens, items, model)

        call = APICall(
            timestamp=datetime.now().isoformat(),
            service=service,
            operation=operation,
            tokens=tokens,
            items=items,
            duration_ms=duration_ms,
            status=status,
            cost_usd=cost
        )

        self.session_calls.append(call)
        self._persist_call(call)

        logger.debug(
            f"API call tracked: {service}.{operation} - "
            f"{tokens} tokens, ${cost:.6f}, {duration_ms:.2f}ms"
        )

    def _estimate_cost(
        self,
        service: str,
        operation: str,
        tokens: int,
        items: int,
        model: Optional[str]
    ) -> float:
        """
        Estimate cost of API call.

        Args:
            service: Service name
            operation: Operation name
            tokens: Number of tokens
            items: Number of items
            model: Model name

        Returns:
            Estimated cost in USD
        """
        try:
            if service == 'gemini':
                model_name = model or 'text-embedding-004'
                if model_name in self.PRICING['gemini']:
                    rate = self.PRICING['gemini'][model_name]['per_1k_chars']
                    return (tokens / 1000) * rate

            elif service == 'pinecone':
                if operation in self.PRICING['pinecone']:
                    rate = self.PRICING['pinecone'][operation]['per_1k']
                    return (items / 1000) * rate

            elif service == 'openai':
                model_name = model or 'text-embedding-3-small'
                if model_name in self.PRICING['openai']:
                    rate = self.PRICING['openai'][model_name]['per_1k_tokens']
                    return (tokens / 1000) * rate

        except Exception as e:
            logger.error(f"Error estimating cost: {e}")

        return 0.0

    def _persist_call(self, call: APICall):
        """
        Persist API call to storage.

        Args:
            call: APICall to persist
        """
        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(asdict(call)) + '\n')
        except Exception as e:
            logger.error(f"Failed to persist API call: {e}")

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics for current session.

        Returns:
            Dictionary with session stats
        """
        total_calls = len(self.session_calls)
        total_cost = sum(call.cost_usd for call in self.session_calls)
        total_tokens = sum(call.tokens for call in self.session_calls)
        avg_duration = (
            sum(call.duration_ms for call in self.session_calls) / total_calls
            if total_calls > 0 else 0
        )

        # Group by service
        by_service: Dict[str, Dict[str, Any]] = {}
        for call in self.session_calls:
            if call.service not in by_service:
                by_service[call.service] = {
                    'calls': 0,
                    'tokens': 0,
                    'cost': 0.0,
                    'errors': 0
                }

            by_service[call.service]['calls'] += 1
            by_service[call.service]['tokens'] += call.tokens
            by_service[call.service]['cost'] += call.cost_usd

            if call.status == 'error':
                by_service[call.service]['errors'] += 1

        return {
            'total_calls': total_calls,
            'total_cost_usd': round(total_cost, 6),
            'total_tokens': total_tokens,
            'avg_duration_ms': round(avg_duration, 2),
            'by_service': by_service
        }

    def get_historical_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get historical statistics.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with historical stats
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        calls: List[APICall] = []

        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            call_time = datetime.fromisoformat(data['timestamp'])

                            if call_time >= cutoff_date:
                                calls.append(APICall(**data))
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Failed to read historical stats: {e}")

        if not calls:
            return {
                'period_days': days,
                'total_calls': 0,
                'total_cost_usd': 0.0,
                'by_service': {}
            }

        total_cost = sum(call.cost_usd for call in calls)
        total_calls = len(calls)

        # Group by service
        by_service: Dict[str, Dict[str, Any]] = {}
        for call in calls:
            if call.service not in by_service:
                by_service[call.service] = {
                    'calls': 0,
                    'tokens': 0,
                    'cost': 0.0
                }

            by_service[call.service]['calls'] += 1
            by_service[call.service]['tokens'] += call.tokens
            by_service[call.service]['cost'] += call.cost_usd

        # Daily breakdown
        by_day: Dict[str, float] = {}
        for call in calls:
            day = datetime.fromisoformat(call.timestamp).date().isoformat()
            by_day[day] = by_day.get(day, 0.0) + call.cost_usd

        return {
            'period_days': days,
            'total_calls': total_calls,
            'total_cost_usd': round(total_cost, 6),
            'by_service': by_service,
            'by_day': by_day,
            'avg_cost_per_day': round(total_cost / days, 6)
        }

    def get_cost_alert(self, daily_limit_usd: float = 1.0) -> Optional[str]:
        """
        Check if costs exceed daily limit.

        Args:
            daily_limit_usd: Daily cost limit in USD

        Returns:
            Alert message if limit exceeded, None otherwise
        """
        today_stats = self.get_historical_stats(days=1)
        today_cost = today_stats['total_cost_usd']

        if today_cost >= daily_limit_usd:
            return (
                f"⚠ Daily cost limit exceeded: ${today_cost:.4f} / ${daily_limit_usd:.4f}"
            )

        elif today_cost >= daily_limit_usd * 0.8:
            return (
                f"ℹ Approaching daily cost limit: ${today_cost:.4f} / ${daily_limit_usd:.4f}"
            )

        return None


# Global tracker instance
_tracker_instance: Optional[APITracker] = None


def get_api_tracker() -> APITracker:
    """
    Get global API tracker instance.

    Returns:
        APITracker instance
    """
    global _tracker_instance

    if _tracker_instance is None:
        _tracker_instance = APITracker()

    return _tracker_instance


def track_api_call(
    service: str,
    operation: str,
    tokens: int = 0,
    items: int = 0,
    duration_ms: float = 0.0,
    status: str = "success",
    model: Optional[str] = None
):
    """
    Convenience function to track an API call.

    Args:
        service: Service name
        operation: Operation name
        tokens: Number of tokens processed
        items: Number of items processed
        duration_ms: Duration in milliseconds
        status: Call status
        model: Model name
    """
    tracker = get_api_tracker()
    tracker.track_call(service, operation, tokens, items, duration_ms, status, model)
