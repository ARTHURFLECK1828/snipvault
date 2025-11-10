"""
Usage statistics tracking for SnipVault.

Tracks searches, views, and popular snippets.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import Counter
from dataclasses import dataclass, asdict
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UsageEvent:
    """A usage event record."""

    timestamp: str
    event_type: str  # search, view, add, update, delete
    snippet_id: Optional[int] = None
    query: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None


class UsageTracker:
    """Track and analyze usage statistics."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize usage tracker.

        Args:
            storage_path: Path to usage log file
        """
        self.storage_path = storage_path or (
            Path.home() / '.snipvault' / 'usage.jsonl'
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def track_event(
        self,
        event_type: str,
        snippet_id: Optional[int] = None,
        query: Optional[str] = None,
        language: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Track a usage event.

        Args:
            event_type: Type of event
            snippet_id: Snippet ID (if applicable)
            query: Search query (if applicable)
            language: Language filter (if applicable)
            tags: Tags filter (if applicable)
        """
        event = UsageEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            snippet_id=snippet_id,
            query=query,
            language=language,
            tags=tags
        )

        try:
            with open(self.storage_path, 'a') as f:
                f.write(json.dumps(asdict(event)) + '\n')

            logger.debug(f"Usage event tracked: {event_type}")

        except Exception as e:
            logger.error(f"Failed to track usage event: {e}")

    def get_events(self, days: int = 30) -> List[UsageEvent]:
        """
        Get usage events from the last N days.

        Args:
            days: Number of days to look back

        Returns:
            List of usage events
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        events = []

        if not self.storage_path.exists():
            return events

        try:
            with open(self.storage_path, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(data['timestamp'])

                        if event_time >= cutoff_date:
                            events.append(UsageEvent(**data))

                    except Exception:
                        continue

        except Exception as e:
            logger.error(f"Failed to read usage events: {e}")

        return events

    def get_search_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get search statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with search stats
        """
        events = self.get_events(days)
        search_events = [e for e in events if e.event_type == 'search']

        if not search_events:
            return {
                'total_searches': 0,
                'unique_queries': 0,
                'top_queries': [],
                'top_languages': [],
                'top_tags': []
            }

        queries = [e.query for e in search_events if e.query]
        languages = [e.language for e in search_events if e.language]

        all_tags = []
        for e in search_events:
            if e.tags:
                all_tags.extend(e.tags)

        query_counter = Counter(queries)
        language_counter = Counter(languages)
        tag_counter = Counter(all_tags)

        return {
            'total_searches': len(search_events),
            'unique_queries': len(set(queries)),
            'top_queries': query_counter.most_common(10),
            'top_languages': language_counter.most_common(10),
            'top_tags': tag_counter.most_common(10),
            'avg_searches_per_day': len(search_events) / days
        }

    def get_snippet_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get snippet view/interaction statistics.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with snippet stats
        """
        events = self.get_events(days)
        view_events = [e for e in events if e.event_type == 'view' and e.snippet_id]
        add_events = [e for e in events if e.event_type == 'add']
        update_events = [e for e in events if e.event_type == 'update']
        delete_events = [e for e in events if e.event_type == 'delete']

        snippet_views = [e.snippet_id for e in view_events]
        view_counter = Counter(snippet_views)

        return {
            'total_views': len(view_events),
            'unique_snippets_viewed': len(set(snippet_views)),
            'most_viewed_snippets': view_counter.most_common(10),
            'snippets_added': len(add_events),
            'snippets_updated': len(update_events),
            'snippets_deleted': len(delete_events),
            'avg_views_per_day': len(view_events) / days
        }

    def get_activity_timeline(self, days: int = 30) -> Dict[str, int]:
        """
        Get daily activity counts.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary mapping date to event count
        """
        events = self.get_events(days)
        daily_counts = Counter()

        for event in events:
            event_date = datetime.fromisoformat(event.timestamp).date()
            daily_counts[event_date.isoformat()] += 1

        # Fill in missing dates with 0
        start_date = datetime.now().date() - timedelta(days=days)
        timeline = {}

        for i in range(days):
            date = (start_date + timedelta(days=i)).isoformat()
            timeline[date] = daily_counts.get(date, 0)

        return timeline

    def get_summary_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive usage summary.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with usage summary
        """
        events = self.get_events(days)

        return {
            'period_days': days,
            'total_events': len(events),
            'event_breakdown': dict(Counter(e.event_type for e in events)),
            'search_stats': self.get_search_stats(days),
            'snippet_stats': self.get_snippet_stats(days),
            'activity_timeline': self.get_activity_timeline(days)
        }


# Global tracker instance
_tracker_instance: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """
    Get global usage tracker instance.

    Returns:
        UsageTracker instance
    """
    global _tracker_instance

    if _tracker_instance is None:
        _tracker_instance = UsageTracker()

    return _tracker_instance


def track_usage(
    event_type: str,
    snippet_id: Optional[int] = None,
    query: Optional[str] = None,
    language: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """
    Convenience function to track usage.

    Args:
        event_type: Event type
        snippet_id: Snippet ID
        query: Search query
        language: Language filter
        tags: Tags filter
    """
    tracker = get_usage_tracker()
    tracker.track_event(event_type, snippet_id, query, language, tags)
