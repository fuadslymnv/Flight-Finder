import pytest
from datetime import date, datetime, timedelta
from backend.core.models import FlightLeg, FlightSegment, SearchParameters
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.provider import FareProvider
from backend.core.settings import load_settings


class MockProvider(FareProvider):
    async def get_one_way_fares(self, origins, destinations, date_from, date_to, airlines=None, currency="EUR", direct_only=True):
        return []


def create_sample_leg(
    id: str,
    origin: str,
    destination: str,
    dep_dt: datetime,
    arr_dt: datetime,
    carrier: str = "W6",
    price: float = 20.0,
    currency: str = "EUR"
) -> FlightLeg:
    return FlightLeg(
        id=id,
        origin=origin,
        destination=destination,
        origin_city=origin,
        destination_city=destination,
        departure_time=dep_dt,
        arrival_time=arr_dt,
        departure_date=dep_dt.date(),
        carrier_code=carrier,
        carrier_name="Wizz Air" if carrier == "W6" else "Ryanair",
        flight_number=f"{carrier}123",
        price=price,
        currency=currency,
        booking_url=f"https://kiwi.com/u/{id}",
        direct_airline_url=f"https://airline.com/{id}",
        segments=[
            FlightSegment(
                departure_airport=origin,
                arrival_airport=destination,
                departure_time=dep_dt,
                arrival_time=arr_dt,
                carrier_code=carrier,
                carrier_name="Wizz Air",
                flight_number=f"{carrier}123",
            )
        ]
    )


def test_weekday_and_night_filtering():
    engine = FlightEngine(provider=MockProvider(), cache=FlightCache())

    # Outbound on Friday (2026-10-16 is Friday)
    fri_dep = datetime(2026, 10, 16, 6, 0)
    fri_arr = datetime(2026, 10, 16, 8, 0)
    out_fri = create_sample_leg("out_fri", "BUD", "MXP", fri_dep, fri_arr, "FR", 25.0)

    # Outbound on Wednesday (2026-10-14 is Wednesday)
    wed_dep = datetime(2026, 10, 14, 6, 0)
    wed_arr = datetime(2026, 10, 14, 8, 0)
    out_wed = create_sample_leg("out_wed", "BUD", "MXP", wed_dep, wed_arr, "FR", 20.0)

    # Inbound 2 nights later on Sunday (2026-10-18)
    sun_dep = datetime(2026, 10, 18, 18, 0)
    sun_arr = datetime(2026, 10, 18, 20, 0)
    in_sun = create_sample_leg("in_sun", "MXP", "BUD", sun_dep, sun_arr, "W6", 30.0)

    # Inbound 5 nights later (2026-10-21)
    long_dep = datetime(2026, 10, 21, 18, 0)
    long_arr = datetime(2026, 10, 21, 20, 0)
    in_long = create_sample_leg("in_long", "MXP", "BUD", long_dep, long_arr, "W6", 15.0)

    # Search for Friday/Saturday departures, 2-3 nights
    params = SearchParameters(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        departure_weekdays=[4, 5],  # Fri, Sat
        min_nights=2,
        max_nights=3,
        allow_open_jaw=True,
    )

    combos = engine.combine_legs([out_fri, out_wed], [in_sun, in_long], params)
    
    # Should only match out_fri with in_sun (Friday + 2 nights = Sunday)
    assert len(combos) == 1
    it = combos[0]
    assert it.outbound.id == "out_fri"
    assert it.inbound.id == "in_sun"
    assert it.nights == 2
    assert it.total_price == 55.0
    assert it.is_open_jaw is False


def test_open_jaw_combination():
    engine = FlightEngine(provider=MockProvider(), cache=FlightCache())

    # Outbound from BUD -> STN on Saturday
    sat_dep = datetime(2026, 10, 17, 7, 0)
    sat_arr = datetime(2026, 10, 17, 9, 0)
    out_bud = create_sample_leg("out_bud", "BUD", "STN", sat_dep, sat_arr, "FR", 30.0)

    # Return from STN -> BTS on Monday (2 nights later)
    mon_dep = datetime(2026, 10, 19, 19, 0)
    mon_arr = datetime(2026, 10, 19, 21, 0)
    in_bts = create_sample_leg("in_bts", "STN", "BTS", mon_dep, mon_arr, "W6", 20.0)

    # 1. Allow Open-Jaw = True
    params_oj = SearchParameters(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        departure_weekdays=[4, 5],
        min_nights=2,
        max_nights=3,
        allow_open_jaw=True,
        include_ground_transfer_cost=False,
    )

    combos = engine.combine_legs([out_bud], [in_bts], params_oj)
    assert len(combos) == 1
    assert combos[0].is_open_jaw is True
    assert combos[0].flight_price_total == 50.0
    assert combos[0].total_price == 50.0
    assert combos[0].ground_transfer is not None
    assert combos[0].ground_transfer.origin_airport == "BUD"
    assert combos[0].ground_transfer.return_airport == "BTS"

    # 2. Allow Open-Jaw = False
    params_no_oj = SearchParameters(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        departure_weekdays=[4, 5],
        min_nights=2,
        max_nights=3,
        allow_open_jaw=False,
    )
    combos_no_oj = engine.combine_legs([out_bud], [in_bts], params_no_oj)
    assert len(combos_no_oj) == 0

    # 3. Include Ground Transfer Cost = True
    params_cost = SearchParameters(
        date_from=date(2026, 10, 1),
        date_to=date(2026, 10, 31),
        departure_weekdays=[4, 5],
        min_nights=2,
        max_nights=3,
        allow_open_jaw=True,
        include_ground_transfer_cost=True,
    )
    combos_cost = engine.combine_legs([out_bud], [in_bts], params_cost)
    assert len(combos_cost) == 1
    # Base 50 + 15 ground transfer = 65 EUR
    assert combos_cost[0].ground_transfer_cost == 15.0
    assert combos_cost[0].total_price == 65.0
