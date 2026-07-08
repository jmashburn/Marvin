#!/usr/bin/env python3
"""
Test Event Consumer

A simple event consumer that listens to the event bus and logs all events
to the console and a file. Use this to verify event dispatching is working
across all controllers.

Usage:
    python scripts/test_event_consumer.py
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from sqlalchemy.orm import Session

from marvin.core.root_logger import get_logger
from marvin.db.db_setup import session_context
from marvin.db.models.events import EventsModel

logger = get_logger(__name__)


class EventConsumer:
    """Simple event consumer that polls for new events and logs them."""

    def __init__(self, output_file: str | None = None):
        """
        Initialize the event consumer.

        Args:
            output_file: Optional file path to write events to (in addition to console)
        """
        self.output_file = output_file
        self.last_event_id: str | None = None
        self.event_count = 0

        if output_file:
            # Create output file with header
            with open(output_file, "w") as f:
                f.write("=== Event Consumer Log ===\n")
                f.write(f"Started: {datetime.now(UTC).isoformat()}\n\n")

    def format_event(self, event: EventsModel) -> str:
        """
        Format an event for display.

        Args:
            event: The event model to format

        Returns:
            Formatted string representation
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"Event #{self.event_count}")
        lines.append(f"Type: {event.event_type}")
        lines.append(f"Time: {event.timestamp}")
        lines.append(f"Integration: {event.integration_id}")
        lines.append(f"Group ID: {event.group_id}")
        lines.append(f"Message: {event.message_title}")
        if event.message_body and event.message_body != "generic":
            lines.append(f"Body: {event.message_body}")

        # Parse and display document data
        if event.document_data:
            lines.append("Document Data:")
            try:
                doc_data = json.loads(event.document_data) if isinstance(event.document_data, str) else event.document_data
                for key, value in doc_data.items():
                    if key not in ["document_type", "operation"]:  # Skip metadata
                        lines.append(f"  {key}: {value}")
            except Exception as e:
                lines.append(f"  (Error parsing: {e})")

        lines.append("=" * 80)
        return "\n".join(lines)

    def log_event(self, event: EventsModel) -> None:
        """
        Log an event to console and optionally to file.

        Args:
            event: The event to log
        """
        self.event_count += 1
        formatted = self.format_event(event)

        # Print to console
        print(formatted)

        # Write to file if configured
        if self.output_file:
            with open(self.output_file, "a") as f:
                f.write(formatted + "\n\n")

    def poll_events(self, session: Session, limit: int = 100) -> list[EventsModel]:
        """
        Poll for new events since the last check.

        Args:
            session: Database session
            limit: Maximum number of events to fetch

        Returns:
            List of new events
        """
        query = select(EventsModel).order_by(EventsModel.timestamp.asc())

        if self.last_event_id:
            # Get events after the last one we saw
            last_event = session.query(EventsModel).filter(EventsModel.id == self.last_event_id).first()
            if last_event:
                query = query.filter(EventsModel.timestamp > last_event.timestamp)

        query = query.limit(limit)
        return list(session.execute(query).scalars().all())

    def consume_existing_events(self, show_all: bool = False) -> None:
        """
        Consume and display existing events from the database.

        Args:
            show_all: If True, show all events. If False, only show recent events.
        """
        with session_context() as session:
            query = select(EventsModel).order_by(EventsModel.timestamp.desc())

            if not show_all:
                # Only show events from the last 24 hours
                from datetime import timedelta

                since = datetime.now(UTC) - timedelta(hours=24)
                query = query.filter(EventsModel.timestamp >= since)

            query = query.limit(100)  # Cap at 100 events
            events = list(session.execute(query).scalars().all())

            if not events:
                print("No events found.")
                return

            print(f"\n{'=' * 80}")
            print(f"Found {len(events)} event(s)")
            print(f"{'=' * 80}\n")

            # Display in chronological order
            for event in reversed(events):
                self.log_event(event)

            # Track the latest event
            if events:
                self.last_event_id = str(events[0].id)

    def run_once(self) -> None:
        """Run the consumer once to show recent events."""
        print("\n🎧 Event Consumer - Showing Recent Events")
        print("=" * 80)
        self.consume_existing_events(show_all=False)

        if self.output_file:
            print(f"\n📝 Events also written to: {self.output_file}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Event Consumer")
    parser.add_argument("--all", action="store_true", help="Show all events (not just recent)")
    parser.add_argument("--output", type=str, help="Output file path for event log")
    args = parser.parse_args()

    # Create output file path
    output_file = args.output
    if not output_file:
        output_dir = Path(__file__).parent.parent / "tmp"
        output_dir.mkdir(exist_ok=True)
        output_file = str(output_dir / f"event_log_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.txt")

    consumer = EventConsumer(output_file=output_file)
    consumer.consume_existing_events(show_all=args.all)

    if output_file:
        print(f"\n📝 Events written to: {output_file}")


if __name__ == "__main__":
    main()
