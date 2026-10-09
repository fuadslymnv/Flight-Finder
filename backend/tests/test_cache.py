import tempfile
from pathlib import Path
from datetime import date, datetime
from backend.core.models import FlightLeg
from backend.core.cache import FlightCache


def test_cache_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_cache.db"
        cache = FlightCache(db_path=db_path, default_ttl_hours=1)

        leg1 = FlightLeg(
            id="leg_1",
            origin="BUD",
            destination="STN",
            departure_time=datetime(2026, 10, 20, 6, 0),
            arrival_time=datetime(2026, 10, 20, 8, 0),
            departure_date=date(2026, 10, 20),
            carrier_code="FR",
            carrier_name="Ryanair",
            flight_number="FR123",
            price=29.99,
            currency="EUR",
        )

        # Save to cache
        cache.save_legs([leg1])

        # Query cache
        cached = cache.get_legs(
            origins=["BUD"],
            destinations=["STN"],
            date_from=date(2026, 10, 15),
            date_to=date(2026, 10, 25),
            currency="EUR",
            airlines=["FR", "W6"],
        )
        assert len(cached) == 1
        assert cached[0].id == "leg_1"
        assert cached[0].price == 29.99

        # Expired query test
        cache.save_legs([leg1], ttl_seconds=-10)  # already expired
        expired = cache.get_legs(
            origins=["BUD"],
            destinations=["STN"],
            date_from=date(2026, 10, 15),
            date_to=date(2026, 10, 25),
            currency="EUR",
        )
        assert len(expired) == 0
