import pytest
from datetime import date
from backend.core.parser import parse_natural_language_query
from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.settings import load_settings


@pytest.mark.anyio
async def test_acceptance_criteria_live():
    query = "Find me a cheap 2-3 night flight, depart Friday or Saturday, next 2 months"
    params = parse_natural_language_query(query)

    assert set(params.departure_weekdays) == {4, 5}  # Fri, Sat
    assert params.min_nights == 2
    assert params.max_nights == 3
    assert params.allow_open_jaw is True

    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    # Execute search
    results = await engine.search(params)

    # Verify we got results
    assert len(results) > 0, "Acceptance query should return at least one valid round-trip"

    ALLOWED_AIRLINES = {"W6", "W9", "FR", "RK"}
    ALLOWED_HOME_AIRPORTS = {"BUD", "DEB", "BTS"}

    for it in results:
        # Check departures strictly on Friday (4) or Saturday (5)
        out_weekday = it.outbound.departure_date.weekday()
        assert out_weekday in {4, 5}, f"Outbound date {it.outbound.departure_date} must be Fri or Sat"

        # Check trip length strictly 2 or 3 nights
        assert it.nights in {2, 3}, f"Nights {it.nights} must be 2 or 3"

        # Check origins and return destinations
        assert it.outbound.origin in ALLOWED_HOME_AIRPORTS, f"Outbound origin {it.outbound.origin} must be one of home airports"
        assert it.inbound.destination in ALLOWED_HOME_AIRPORTS, f"Inbound destination {it.inbound.destination} must be one of home airports"

        # Check airlines strictly Wizz Air / Ryanair
        assert it.outbound.carrier_code.upper() in ALLOWED_AIRLINES, f"Outbound carrier {it.outbound.carrier_code} must be Wizz/Ryanair"
        assert it.inbound.carrier_code.upper() in ALLOWED_AIRLINES, f"Inbound carrier {it.inbound.carrier_code} must be Wizz/Ryanair"

        # Check prices calculation
        expected_total = it.flight_price_total + it.ground_transfer_cost
        assert abs(it.total_price - expected_total) < 0.01

    # Verify results are sorted by total price
    prices = [it.total_price for it in results]
    assert prices == sorted(prices), "Results must be sorted by total price ascending"
