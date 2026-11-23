"""
Unit tests for Weekend Deal Scanner, Telegram Notifier, Alert Tracker, and Scheduler.
"""

import pytest
from datetime import date, datetime, timedelta
from backend.core.models import (
    FlightLeg,
    FlightSegment,
    SearchParameters,
    WeekendAlertSettings,
    RoundTripItinerary,
)
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.provider import FareProvider
from backend.core.weekend import build_weekend_search_params, find_weekend_deals
from backend.services.alert_tracker import AlertTracker
from backend.services.telegram_notifier import TelegramNotifier
from backend.services.scheduler import get_schedule_hours, get_next_run_time


class MockProvider(FareProvider):
    def __init__(self, legs=None):
        self.legs = legs or []

    async def get_one_way_fares(self, origins, destinations, date_from, date_to, airlines=None, currency="EUR", direct_only=True):
        return self.legs


def make_leg(
    leg_id: str,
    origin: str,
    dest: str,
    dep_dt: datetime,
    arr_dt: datetime,
    carrier: str = "FR",
    price: float = 25.0,
    currency: str = "EUR",
) -> FlightLeg:
    return FlightLeg(
        id=leg_id,
        origin=origin,
        destination=dest,
        origin_city=origin,
        destination_city=dest,
        departure_time=dep_dt,
        arrival_time=arr_dt,
        departure_date=dep_dt.date(),
        carrier_code=carrier,
        carrier_name="Ryanair" if carrier == "FR" else "Wizz Air",
        flight_number=f"{carrier}101",
        price=price,
        currency=currency,
        booking_url=f"https://kiwi.com/{leg_id}",
        direct_airline_url=f"https://airline.com/{leg_id}",
        segments=[
            FlightSegment(
                departure_airport=origin,
                arrival_airport=dest,
                departure_time=dep_dt,
                arrival_time=arr_dt,
                carrier_code=carrier,
                carrier_name="Ryanair",
                flight_number=f"{carrier}101",
            )
        ],
    )


def test_schedule_hours_generation():
    hours = get_schedule_hours(start_hour=9, interval_hours=6)
    assert hours == [3, 9, 15, 21]


def test_next_run_time_calculation():
    # If now is 08:30, next should be 09:00 today
    t1 = datetime(2026, 11, 24, 8, 30, 0)
    next_1 = get_next_run_time(t1, start_hour=9, interval_hours=6)
    assert next_1 == datetime(2026, 11, 24, 9, 0, 0)

    # If now is 09:15, next should be 15:00 today
    t2 = datetime(2026, 11, 24, 9, 15, 0)
    next_2 = get_next_run_time(t2, start_hour=9, interval_hours=6)
    assert next_2 == datetime(2026, 11, 24, 15, 0, 0)

    # If now is 22:30, next should be 03:00 tomorrow
    t3 = datetime(2026, 11, 24, 22, 30, 0)
    next_3 = get_next_run_time(t3, start_hour=9, interval_hours=6)
    assert next_3 == datetime(2026, 11, 25, 3, 0, 0)


def test_weekend_params_builder():
    cfg = WeekendAlertSettings(
        max_price=55.0,
        horizon_days=60,
        allow_open_jaw=True,
    )
    base = date(2026, 11, 24)
    params = build_weekend_search_params(cfg, base_date=base)

    assert params.max_price == 55.0
    assert params.date_from == base
    assert params.date_to == base + timedelta(days=60)
    assert params.departure_weekdays == [4, 5]  # Friday, Saturday
    assert params.return_weekdays == [6, 0]     # Sunday, Monday
    assert params.max_monday_arrival_hour == 9
    assert params.allow_open_jaw is True


def test_monday_arrival_time_filtering():
    """Verify that Monday returns landing after 09:00 are rejected for 9-5 workers."""
    engine = FlightEngine(provider=MockProvider(), cache=FlightCache())

    # Friday 2026-12-04 departure (Friday is day 4)
    out_fri = make_leg("out1", "BUD", "FCO", datetime(2026, 12, 4, 18, 0), datetime(2026, 12, 4, 19, 45), price=25.0)

    # Monday 2026-12-07 returns:
    # 1. Early morning return landing at 08:15 (Accepted)
    ret_mon_early = make_leg("ret_early", "FCO", "BUD", datetime(2026, 12, 7, 6, 30), datetime(2026, 12, 7, 8, 15), price=25.0)

    # 2. Late morning return landing at 11:30 (Rejected: landing after 9 AM)
    ret_mon_late = make_leg("ret_late", "FCO", "BUD", datetime(2026, 12, 7, 9, 45), datetime(2026, 12, 7, 11, 30), price=20.0)

    # 3. Sunday return landing at 22:00 (Accepted: Sunday has no 9 AM constraint)
    ret_sun = make_leg("ret_sun", "FCO", "BUD", datetime(2026, 12, 6, 20, 0), datetime(2026, 12, 6, 22, 0), price=30.0)

    params = SearchParameters(
        origins=["BUD"],
        destination="FCO",
        date_from=date(2026, 12, 1),
        date_to=date(2026, 12, 10),
        min_nights=1,
        max_nights=4,
        departure_weekdays=[4, 5],
        return_weekdays=[6, 0],
        max_monday_arrival_hour=9,
        allow_open_jaw=True,
    )

    results = engine.combine_legs([out_fri], [ret_mon_early, ret_mon_late, ret_sun], params)

    assert len(results) == 2
    inbound_ids = {r.inbound.id for r in results}
    assert "ret_early" in inbound_ids
    assert "ret_sun" in inbound_ids
    assert "ret_late" not in inbound_ids  # Rejected!


def test_open_jaw_weekend_combination():
    """Verify open-jaw pairing BUD ➔ FCO ➔ BTS with ground transfer."""
    engine = FlightEngine(provider=MockProvider(), cache=FlightCache())

    # Friday BUD -> FCO
    out = make_leg("out_oj", "BUD", "FCO", datetime(2026, 12, 4, 18, 0), datetime(2026, 12, 4, 19, 45), price=20.0)
    # Sunday FCO -> BTS (Open-jaw return to Bratislava)
    ret = make_leg("ret_oj", "FCO", "BTS", datetime(2026, 12, 6, 20, 0), datetime(2026, 12, 6, 21, 45), price=25.0)

    params = SearchParameters(
        origins=["BUD", "BTS"],
        destination="FCO",
        date_from=date(2026, 12, 1),
        date_to=date(2026, 12, 10),
        min_nights=2,
        max_nights=3,
        allow_open_jaw=True,
        include_ground_transfer_cost=True,
    )

    combos = engine.combine_legs([out], [ret], params)
    assert len(combos) == 1
    it = combos[0]
    assert it.is_open_jaw is True
    assert it.flight_price_total == 45.0
    assert it.ground_transfer is not None
    assert it.ground_transfer.return_airport == "BTS"
    assert it.ground_transfer.origin_airport == "BUD"
    assert it.total_price == 45.0 + it.ground_transfer_cost


def test_alert_tracker_deduplication(tmp_path):
    db_file = tmp_path / "test_alerts.db"
    tracker = AlertTracker(db_path=db_file)

    out = make_leg("out1", "BUD", "FCO", datetime(2026, 12, 4, 18, 0), datetime(2026, 12, 4, 19, 45), price=25.0)
    ret = make_leg("ret1", "FCO", "BUD", datetime(2026, 12, 6, 20, 0), datetime(2026, 12, 6, 22, 0), price=25.0)

    it = RoundTripItinerary(
        id="rt_1",
        outbound=out,
        inbound=ret,
        nights=2,
        is_open_jaw=False,
        flight_price_total=50.0,
        total_price=50.0,
        currency="EUR",
        destination_city="Rome",
    )

    # 1. Fresh on first check
    assert tracker.is_deal_fresh(it) is True

    # 2. Record it as sent
    tracker.record_sent_deals([it])

    # 3. Same deal at same price should no longer be fresh
    assert tracker.is_deal_fresh(it) is False

    # 4. If price drops to 45.0, it should be fresh again!
    cheaper_it = it.model_copy(update={"total_price": 45.0})
    assert tracker.is_deal_fresh(cheaper_it) is True


def test_telegram_message_formatter():
    notifier = TelegramNotifier(bot_token="test_token", chat_id="123456")
    out = make_leg("out1", "BUD", "FCO", datetime(2026, 12, 4, 18, 0), datetime(2026, 12, 4, 19, 45), price=25.0)
    ret = make_leg("ret1", "FCO", "BTS", datetime(2026, 12, 6, 20, 0), datetime(2026, 12, 6, 22, 0), price=25.0)

    it = RoundTripItinerary(
        id="rt_test",
        outbound=out,
        inbound=ret,
        nights=2,
        is_open_jaw=True,
        flight_price_total=50.0,
        total_price=50.0,
        currency="EUR",
        destination_city="Rome",
    )

    msg = notifier.format_deal_message(it)
    assert "ROME" in msg
    assert "50" in msg
    assert "BUD ➔ FCO ➔ BTS" in msg
    assert "Open-Jaw" in msg
    assert "Outbound:" in msg
    assert "Return:" in msg
