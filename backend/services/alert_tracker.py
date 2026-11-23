"""
Alert Tracker & Deduplication Service.
Keeps track of dispatched flight deals to avoid repeating identical alerts
unless the deal is new or the price has dropped.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from backend.core.models import RoundTripItinerary

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "flight_cache.db"


class AlertTracker:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_history (
                    deal_key TEXT PRIMARY KEY,
                    outbound_flight TEXT,
                    return_flight TEXT,
                    origin TEXT,
                    destination TEXT,
                    return_destination TEXT,
                    outbound_date TEXT,
                    return_date TEXT,
                    price REAL,
                    currency TEXT,
                    is_open_jaw INTEGER,
                    sent_at TEXT
                )
                """
            )
            conn.commit()

    @staticmethod
    def get_deal_key(it: RoundTripItinerary) -> str:
        """Construct a stable unique key for a flight deal."""
        out = it.outbound
        ret = it.inbound
        return f"{out.origin}_{out.destination}_{ret.destination}_{out.departure_date}_{ret.departure_date}"

    def is_deal_fresh(self, it: RoundTripItinerary, re_alert_days: int = 3) -> bool:
        """
        Check if a deal should be alerted:
        - True if never sent
        - True if price dropped by at least 1 unit
        - True if previously sent more than `re_alert_days` ago
        - False if recently sent at the same or higher price
        """
        key = self.get_deal_key(it)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT price, sent_at FROM alert_history WHERE deal_key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return True

            prev_price = float(row["price"])
            sent_at = datetime.fromisoformat(row["sent_at"])

            # If price dropped by at least 1 unit
            if it.total_price < (prev_price - 0.5):
                return True

            # If last sent older than threshold
            if (datetime.now() - sent_at) > timedelta(days=re_alert_days):
                return True

            return False

    def filter_fresh_deals(
        self,
        deals: List[RoundTripItinerary],
        re_alert_days: int = 3,
    ) -> List[RoundTripItinerary]:
        """Filter a list of deals to only those that are new or price-dropped."""
        return [d for d in deals if self.is_deal_fresh(d, re_alert_days=re_alert_days)]

    def record_sent_deals(self, deals: List[RoundTripItinerary]):
        """Record dispatched deals into SQLite history."""
        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            for it in deals:
                key = self.get_deal_key(it)
                out = it.outbound
                ret = it.inbound
                conn.execute(
                    """
                    INSERT INTO alert_history (
                        deal_key, outbound_flight, return_flight, origin, destination,
                        return_destination, outbound_date, return_date, price, currency,
                        is_open_jaw, sent_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(deal_key) DO UPDATE SET
                        price = excluded.price,
                        currency = excluded.currency,
                        sent_at = excluded.sent_at
                    """,
                    (
                        key,
                        f"{out.carrier_code}{out.flight_number}",
                        f"{ret.carrier_code}{ret.flight_number}",
                        out.origin,
                        out.destination,
                        ret.destination,
                        str(out.departure_date),
                        str(ret.departure_date),
                        it.total_price,
                        it.currency,
                        1 if it.is_open_jaw else 0,
                        now_str,
                    ),
                )
            conn.commit()

    def get_recent_alert_count(self, hours: int = 24) -> int:
        """Count deals alerted in the past X hours."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM alert_history WHERE sent_at >= ?", (since,))
            row = cursor.fetchone()
            return row["c"] if row else 0

    def clear_history(self):
        """Clear alert history (useful for testing or resetting)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM alert_history")
            conn.commit()
