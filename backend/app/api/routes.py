import logging
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.core.models import (
    SearchParameters,
    RoundTripItinerary,
    ExploreDestinationSummary,
    HeatmapCell,
    AppSettings,
    WeekendAlertSettings,
)
from backend.core.parser import parse_natural_language_query
from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.settings import load_settings, save_settings
from backend.services.telegram_notifier import TelegramNotifier
from backend.services.alert_tracker import AlertTracker
from backend.services.scheduler import run_weekend_alert_cycle

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize singletons
provider = KiwiMcpProvider()
cache = FlightCache()
settings = load_settings()
engine = FlightEngine(provider=provider, cache=cache, settings=settings)


class ParseRequest(BaseModel):
    query: str


class SearchResponse(BaseModel):
    parameters: SearchParameters
    total_results: int
    itineraries: List[RoundTripItinerary]


class CalendarRequest(BaseModel):
    destination: str
    date_from: date
    date_to: date
    min_nights: int = 2
    max_nights: int = 4
    origins: Optional[List[str]] = None
    currency: str = "EUR"
    allow_open_jaw: bool = True


@router.post("/parse", response_model=SearchParameters)
async def parse_query_endpoint(req: ParseRequest):
    """Parse natural language query into structured SearchParameters."""
    try:
        return parse_natural_language_query(req.query)
    except Exception as e:
        logger.error(f"Error parsing query: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_flights_endpoint(params: SearchParameters, force_refresh: bool = False):
    """Search round-trip flight combinations across Wizz Air and Ryanair."""
    try:
        # Reload settings in case ground transfers were updated
        engine.settings = load_settings()
        itineraries = await engine.search(params, force_refresh=force_refresh)
        return SearchResponse(
            parameters=params,
            total_results=len(itineraries),
            itineraries=itineraries,
        )
    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/explore", response_model=List[ExploreDestinationSummary])
async def explore_destinations_endpoint(params: SearchParameters):
    """Get cheapest destinations grouped by city/country for broad explore searches."""
    try:
        engine.settings = load_settings()
        return await engine.get_explore_destinations(params)
    except Exception as e:
        logger.error(f"Error during explore search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendar", response_model=List[HeatmapCell])
async def calendar_heatmap_endpoint(req: CalendarRequest):
    """Generate price heatmap matrix for a destination."""
    try:
        engine.settings = load_settings()
        return await engine.get_calendar_heatmap(
            destination=req.destination,
            date_from=req.date_from,
            date_to=req.date_to,
            min_nights=req.min_nights,
            max_nights=req.max_nights,
            origins=req.origins,
            currency=req.currency,
            allow_open_jaw=req.allow_open_jaw,
        )
    except Exception as e:
        logger.error(f"Error generating calendar heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings", response_model=AppSettings)
async def get_settings_endpoint():
    """Retrieve app settings and ground transfer presets."""
    return load_settings()


@router.put("/settings", response_model=AppSettings)
async def update_settings_endpoint(new_settings: AppSettings):
    """Update app settings and ground transfer presets."""
    save_settings(new_settings)
    engine.settings = new_settings
    return new_settings


@router.post("/cache/clear")
async def clear_cache_endpoint():
    """Clear all cached flight legs."""
    cache.clear_all()
    return {"status": "ok", "message": "Flight cache cleared successfully"}


@router.get("/alerts/config", response_model=WeekendAlertSettings)
async def get_alerts_config_endpoint():
    """Retrieve current weekend deal alert configuration."""
    current_settings = load_settings()
    return current_settings.alerts


@router.put("/alerts/config", response_model=WeekendAlertSettings)
async def update_alerts_config_endpoint(config: WeekendAlertSettings):
    """Update weekend deal alert configuration."""
    current_settings = load_settings()
    current_settings.alerts = config
    save_settings(current_settings)
    engine.settings = current_settings
    return config


@router.post("/alerts/test-telegram")
async def test_telegram_endpoint():
    """Test Telegram Bot connection with current credentials."""
    current_settings = load_settings()
    notifier = TelegramNotifier(config=current_settings.alerts.telegram)
    if not notifier.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Telegram Bot Token or Chat ID is not configured.",
        )
    success, message = await notifier.test_connection()
    if not success:
        raise HTTPException(status_code=502, detail=message)
    return {"status": "ok", "message": message}


class AlertScanResponse(BaseModel):
    total_deals: int
    fresh_deals: int
    dispatched_to_telegram: bool
    itineraries: List[RoundTripItinerary]


@router.post("/alerts/scan", response_model=AlertScanResponse)
async def scan_alerts_endpoint(dry_run: bool = False, force_refresh: bool = False):
    """Trigger an immediate weekend deal scan."""
    try:
        engine.settings = load_settings()
        tracker = AlertTracker()
        notifier = TelegramNotifier(config=engine.settings.alerts.telegram)
        all_deals, fresh = await run_weekend_alert_cycle(
            engine=engine,
            notifier=notifier,
            tracker=tracker,
            force_refresh=force_refresh,
            dry_run=dry_run,
        )
        return AlertScanResponse(
            total_deals=len(all_deals),
            fresh_deals=len(fresh),
            dispatched_to_telegram=notifier.is_configured and not dry_run and len(fresh) > 0,
            itineraries=all_deals,
        )
    except Exception as e:
        logger.error(f"Error during alert scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/clear-history")
async def clear_alert_history_endpoint():
    """Clear previously dispatched deals history to allow re-alerting."""
    tracker = AlertTracker()
    tracker.clear_history()
    return {"status": "ok", "message": "Alert history cleared successfully"}
