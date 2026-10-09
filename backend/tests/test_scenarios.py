import pytest
from datetime import date, datetime, timedelta
from backend.core.parser import parse_natural_language_query
from backend.core.models import SearchParameters, AppSettings, GroundTransferPreset
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.settings import load_settings, save_settings


@pytest.mark.anyio
async def test_scenario_acceptance_workflow():
    """Workflow Scenario 1: Acceptance Test NL Query Execution"""
    query = "cheap 2-3 night trip, leave Fri or Sat, next 2 months"
    params = parse_natural_language_query(query)

    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    results = await engine.search(params)
    assert len(results) > 0

    for it in results:
        # Verify Fri/Sat outbound
        assert it.outbound.departure_date.weekday() in (4, 5)
        # Verify 2-3 nights
        assert it.nights in (2, 3)
        # Verify origin and destination in allowed home airports
        assert it.outbound.origin in ("BUD", "DEB", "BTS")
        assert it.inbound.destination in ("BUD", "DEB", "BTS")
        # Verify Wizz Air / Ryanair only
        assert it.outbound.carrier_code in ("W6", "W9", "FR", "RK")
        assert it.inbound.carrier_code in ("W6", "W9", "FR", "RK")


@pytest.mark.anyio
async def test_scenario_open_jaw_and_ground_transfer_workflow():
    """Workflow Scenario 2: Open-Jaw combinations with ground transfer cost injection"""
    today = date.today()
    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    # Search with Open-Jaw enabled
    params_oj = SearchParameters(
        origins=["BUD", "BTS"],
        destination="London",
        date_from=today + timedelta(days=14),
        date_to=today + timedelta(days=45),
        min_nights=2,
        max_nights=4,
        departure_weekdays=[4, 5],
        allow_open_jaw=True,
        include_ground_transfer_cost=True,
        currency="EUR",
    )

    results = await engine.search(params_oj)
    assert len(results) > 0

    has_open_jaw = False
    for it in results:
        if it.is_open_jaw:
            has_open_jaw = True
            assert it.ground_transfer is not None
            assert it.ground_transfer_cost > 0
            assert it.total_price == round(it.flight_price_total + it.ground_transfer_cost, 2)

    # Search with Open-Jaw disabled
    params_no_oj = params_oj.model_copy(update={"allow_open_jaw": False})
    results_no_oj = await engine.search(params_no_oj)
    for it in results_no_oj:
        assert it.is_open_jaw is False
        assert it.outbound.origin == it.inbound.destination


@pytest.mark.anyio
async def test_scenario_huf_currency_mode():
    """Workflow Scenario 3: Currency switching and HUF price aggregation"""
    today = date.today()
    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    params_huf = SearchParameters(
        origins=["BUD"],
        destination="Milan",
        date_from=today + timedelta(days=14),
        date_to=today + timedelta(days=45),
        min_nights=2,
        max_nights=3,
        departure_weekdays=[4, 5],
        currency="HUF",
    )

    results = await engine.search(params_huf)
    assert len(results) > 0
    for it in results:
        assert it.currency == "HUF"
        assert it.outbound.currency == "HUF"
        assert it.inbound.currency == "HUF"
        assert it.total_price > 1000  # HUF prices in thousands


@pytest.mark.anyio
async def test_scenario_cache_acceleration():
    """Workflow Scenario 4: Fast re-filtering via SQLite cache without remote network calls"""
    today = date.today()
    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    params = SearchParameters(
        origins=["BUD"],
        destination="Rome",
        date_from=today + timedelta(days=14),
        date_to=today + timedelta(days=35),
        min_nights=2,
        max_nights=3,
        departure_weekdays=[4, 5],
        currency="EUR",
    )

    # First search populates cache
    t0 = datetime.now()
    res1 = await engine.search(params)
    t_first = (datetime.now() - t0).total_seconds()

    # Second search with modified ground transfer toggle hits local cache instantly
    params_refilter = params.model_copy(update={"include_ground_transfer_cost": True})
    t1 = datetime.now()
    res2 = await engine.search(params_refilter)
    t_second = (datetime.now() - t1).total_seconds()

    # Second search should be instant (local SQLite, < 0.2s)
    assert t_second < 0.2
    assert len(res2) == len(res1)
