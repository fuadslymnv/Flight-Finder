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
)
from backend.core.parser import parse_natural_language_query
from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.settings import load_settings, save_settings

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
