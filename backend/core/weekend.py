"""
Weekend Deal Discovery Module for 9-5 Weekday Workers.
Finds short weekend roundtrips (Fri/Sat outbound, Sun/early Mon return)
for the next 60 days under a target price (e.g. 60 EUR) with open-jaw support.
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from backend.core.models import SearchParameters, RoundTripItinerary, WeekendAlertSettings
from backend.core.combiner import FlightEngine

logger = logging.getLogger(__name__)


def build_weekend_search_params(
    alert_settings: WeekendAlertSettings,
    base_date: Optional[date] = None,
) -> SearchParameters:
    """Build SearchParameters specifically tailored for weekend getaway deals."""
    today = base_date or date.today()
    return SearchParameters(
        query_text="Weekend Deals (9-5 weekday workers)",
        origins=alert_settings.origins,
        destination="anywhere",
        date_from=today,
        date_to=today + timedelta(days=alert_settings.horizon_days),
        min_nights=alert_settings.min_nights,
        max_nights=alert_settings.max_nights,
        departure_weekdays=alert_settings.outbound_weekdays,
        return_weekdays=alert_settings.return_weekdays,
        max_monday_arrival_hour=alert_settings.max_monday_arrival_hour,
        allow_open_jaw=alert_settings.allow_open_jaw,
        max_price=alert_settings.max_price,
        currency=alert_settings.currency,
    )


async def find_weekend_deals(
    engine: FlightEngine,
    alert_settings: Optional[WeekendAlertSettings] = None,
    force_refresh: bool = False,
    base_date: Optional[date] = None,
) -> List[RoundTripItinerary]:
    """
    Search for all weekend flight deals for the next 60 days
    matching the 9-5 worker schedule constraints and budget.
    """
    settings = alert_settings or engine.settings.alerts
    params = build_weekend_search_params(settings, base_date=base_date)

    logger.info(
        f"Scanning weekend deals: {params.date_from} to {params.date_to}, "
        f"max price: {params.max_price} {params.currency}, open-jaw: {params.allow_open_jaw}"
    )

    itineraries = await engine.search(params, force_refresh=force_refresh)

    # Post-filter verification for 9-5 weekend constraints
    verified_deals: List[RoundTripItinerary] = []
    for it in itineraries:
        out = it.outbound
        ret = it.inbound

        # Check total price
        if settings.max_price is not None and it.total_price > settings.max_price:
            continue

        # Check outbound is Friday (4) or Saturday (5)
        if out.departure_date.weekday() not in settings.outbound_weekdays:
            continue

        # Check return is Sunday (6) or Monday (0)
        if ret.departure_date.weekday() not in settings.return_weekdays:
            continue

        # If returning Monday, ensure arrival time is before/at max_monday_arrival_hour
        if settings.max_monday_arrival_hour is not None and ret.arrival_time.weekday() == 0:
            if ret.arrival_time.hour > settings.max_monday_arrival_hour or (
                ret.arrival_time.hour == settings.max_monday_arrival_hour and ret.arrival_time.minute > 0
            ):
                continue

        verified_deals.append(it)

    verified_deals.sort(key=lambda x: (x.total_price, x.outbound.departure_date))
    return verified_deals
