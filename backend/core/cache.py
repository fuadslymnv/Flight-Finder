import sqlite3
import json
import time
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Union
from backend.core.models import FlightLeg

DEFAULT_CACHE_DB = Path(__file__).resolve().parent.parent.parent / "flight_cache.db"


class FlightCache:
    def __init__(self, db_path: Path = DEFAULT_CACHE_DB, default_ttl_hours: int = 4):
        self.db_path = db_path
        self.default_ttl_seconds = default_ttl_hours * 3600
        self._init_db()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flight_legs (
                    id TEXT PRIMARY KEY,
                    origin TEXT,
                    destination TEXT,
                    origin_city TEXT,
                    destination_city TEXT,
                    destination_country TEXT,
                    departure_date TEXT,
                    departure_time TEXT,
                    carrier_code TEXT,
                    currency TEXT,
                    price REAL,
                    raw_json TEXT,
                    fetched_at REAL,
                    expires_at REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_legs_search 
                ON flight_legs (origin, destination, departure_date, currency, expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_legs_cities 
                ON flight_legs (origin_city, destination_city, destination_country)
            """)
            conn.commit()

    def save_legs(self, legs: List[FlightLeg], ttl_seconds: Optional[int] = None):
        if not legs:
            return
        ttl = ttl_seconds or self.default_ttl_seconds
        now = time.time()
        expires_at = now + ttl

        rows = []
        for leg in legs:
            rows.append((
                leg.id,
                leg.origin.upper(),
                leg.destination.upper(),
                leg.origin_city.upper(),
                leg.destination_city.upper(),
                leg.destination_country.upper(),
                leg.departure_date.isoformat(),
                leg.departure_time.isoformat(),
                leg.carrier_code.upper(),
                leg.currency.upper(),
                leg.price,
                leg.model_dump_json(),
                now,
                expires_at
            ))

        with self._connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO flight_legs 
                (id, origin, destination, origin_city, destination_city, destination_country, departure_date, departure_time, carrier_code, currency, price, raw_json, fetched_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            conn.commit()

    def get_legs(
        self,
        origins: Union[List[str], str],
        destinations: Union[List[str], str],
        date_from: date,
        date_to: date,
        currency: str = "EUR",
        airlines: Optional[List[str]] = None
    ) -> List[FlightLeg]:
        import re
        now = time.time()
        if isinstance(origins, str):
            origin_list = [o.strip().upper() for o in re.split(r'[,/]', origins) if o.strip()]
        else:
            origin_list = [o.upper() for o in origins]

        if isinstance(destinations, str):
            dest_list = [d.strip().upper() for d in re.split(r'[,/]', destinations) if d.strip()]
        else:
            dest_list = [d.upper() for d in destinations]

        where_clauses = [
            "departure_date >= ?",
            "departure_date <= ?",
            "currency = ?",
            "expires_at > ?"
        ]
        params = [date_from.isoformat(), date_to.isoformat(), currency.upper(), now]

        if origin_list and "ANYWHERE" not in origin_list:
            placeholders = ",".join("?" for _ in origin_list)
            where_clauses.append(f"(origin IN ({placeholders}) OR origin_city IN ({placeholders}))")
            params.extend(origin_list * 2)

        if dest_list and "ANYWHERE" not in dest_list:
            placeholders = ",".join("?" for _ in dest_list)
            where_clauses.append(f"(destination IN ({placeholders}) OR destination_city IN ({placeholders}) OR destination_country IN ({placeholders}))")
            params.extend(dest_list * 3)

        if airlines:
            airline_list = [a.upper() for a in airlines]
            placeholders = ",".join("?" for _ in airline_list)
            where_clauses.append(f"carrier_code IN ({placeholders})")
            params.extend(airline_list)

        query = f"""
            SELECT raw_json FROM flight_legs
            WHERE {' AND '.join(where_clauses)}
            ORDER BY price ASC
        """

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row["raw_json"])
                    results.append(FlightLeg.model_validate(data))
                except Exception:
                    continue
            return results

    def clear_expired(self):
        now = time.time()
        with self._connection() as conn:
            conn.execute("DELETE FROM flight_legs WHERE expires_at <= ?", (now,))
            conn.commit()

    def clear_all(self):
        with self._connection() as conn:
            conn.execute("DELETE FROM flight_legs")
            conn.commit()
