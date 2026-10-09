import asyncio
import logging
import re
from datetime import date, timedelta
from typing import List, Dict, Optional, Tuple, Set

from backend.core.models import (
    FlightLeg,
    RoundTripItinerary,
    GroundTransferInfo,
    SearchParameters,
    AppSettings,
    ExploreDestinationSummary,
    HeatmapCell,
)
from backend.core.provider import FareProvider
from backend.core.cache import FlightCache
from backend.core.settings import load_settings

logger = logging.getLogger(__name__)


class FlightEngine:
    def __init__(
        self,
        provider: FareProvider,
        cache: Optional[FlightCache] = None,
        settings: Optional[AppSettings] = None,
    ):
        self.provider = provider
        self.cache = cache or FlightCache()
        self.settings = settings or load_settings()

    def _get_ground_transfer(self, out_origin: str, ret_dest: str, currency: str) -> Optional[GroundTransferInfo]:
        if out_origin == ret_dest:
            return None

        route_key1 = f"{ret_dest}-{out_origin}"
        route_key2 = f"{out_origin}-{ret_dest}"

        preset = self.settings.ground_transfers.get(route_key1) or self.settings.ground_transfers.get(route_key2)
        if preset:
            return GroundTransferInfo(
                required=True,
                origin_airport=out_origin,
                return_airport=ret_dest,
                transit_hours=preset.transit_hours,
                transit_description=preset.description,
                estimated_cost_eur=preset.cost_eur,
                estimated_cost_huf=preset.cost_huf,
            )

        # Fallback default
        return GroundTransferInfo(
            required=True,
            origin_airport=out_origin,
            return_airport=ret_dest,
            transit_hours=3.0,
            transit_description=f"Ground transfer between {ret_dest} and {out_origin}",
            estimated_cost_eur=15.0,
            estimated_cost_huf=6000.0,
        )

    def combine_legs(
        self,
        outbound_legs: List[FlightLeg],
        inbound_legs: List[FlightLeg],
        params: SearchParameters,
    ) -> List[RoundTripItinerary]:
        itineraries: List[RoundTripItinerary] = []
        seen_combos: Set[str] = set()

        # Prepare normalized exclusion set
        excluded_set = {e.upper() for e in params.exclude_destinations}

        is_anywhere = params.destination.strip().lower() in ("anywhere", "everywhere", "", "all")
        dest_targets_lower = [d.strip().lower() for d in re.split(r'[,/]', params.destination) if d.strip()] if not is_anywhere else []

        for out in outbound_legs:
            # Check outbound weekday filter (0=Mon..6=Sun)
            if params.departure_weekdays and out.departure_date.weekday() not in params.departure_weekdays:
                continue

            # Check time-of-day constraints (e.g. Thursday evening departure >= 17:00)
            if params.thursday_evening_only and out.departure_date.weekday() == 3 and out.departure_time.hour < 17:
                continue
            if params.min_outbound_hour is not None and out.departure_time.hour < params.min_outbound_hour:
                continue

            # Check destination exclusions (city, country, or airport code)
            out_dest_terms = {out.destination.upper(), out.destination_city.upper(), out.destination_country.upper()}
            if excluded_set and any(term in excluded_set or any(excl in term for excl in excluded_set) for term in out_dest_terms if term):
                continue

            # Check requested destination target match if specific destinations were provided
            if dest_targets_lower:
                leg_dest_identifiers = {
                    out.destination.lower(),
                    out.destination_city.lower(),
                    out.destination_country.lower(),
                }
                matches_target = False
                for target in dest_targets_lower:
                    for ident in leg_dest_identifiers:
                        if ident and (target == ident or target in ident or ident in target):
                            matches_target = True
                            break
                    if matches_target:
                        break
                if not matches_target:
                    continue

            for ret in inbound_legs:
                # Must match destination (outbound to == inbound from)
                # Or if cities are available and match
                dest_match = (
                    out.destination == ret.origin
                    or (out.destination_city and ret.origin_city and out.destination_city.lower() == ret.origin_city.lower())
                )
                if not dest_match:
                    continue

                # Return date must be >= outbound date
                delta_days = (ret.departure_date - out.departure_date).days
                if delta_days < params.min_nights or delta_days > params.max_nights:
                    continue

                # Return departure time must be after outbound arrival
                if ret.departure_time <= out.arrival_time:
                    continue

                # Check return weekday filter if set
                if params.return_weekdays and ret.departure_date.weekday() not in params.return_weekdays:
                    continue

                is_open_jaw = (out.origin != ret.destination)
                if is_open_jaw and not params.allow_open_jaw:
                    continue

                ground_info = self._get_ground_transfer(out.origin, ret.destination, params.currency) if is_open_jaw else None

                ground_cost = 0.0
                if is_open_jaw and params.include_ground_transfer_cost and ground_info:
                    ground_cost = ground_info.estimated_cost_eur if params.currency == "EUR" else ground_info.estimated_cost_huf

                flight_total = round(out.price + ret.price, 2)
                total_price = round(flight_total + ground_cost, 2)

                if params.max_price is not None and total_price > params.max_price:
                    continue

                combo_key = f"{out.id}_{ret.id}"
                if combo_key in seen_combos:
                    continue
                seen_combos.add(combo_key)

                itineraries.append(
                    RoundTripItinerary(
                        id=f"rt_{combo_key}",
                        outbound=out,
                        inbound=ret,
                        nights=delta_days,
                        is_open_jaw=is_open_jaw,
                        ground_transfer=ground_info,
                        flight_price_total=flight_total,
                        ground_transfer_cost=ground_cost,
                        total_price=total_price,
                        currency=params.currency,
                        destination_city=out.destination_city or ret.origin_city or out.destination,
                        destination_country=out.destination_country or ret.origin_country or "",
                    )
                )

        # Sort by total price ascending
        itineraries.sort(key=lambda x: (x.total_price, x.outbound.departure_time))
        return itineraries

    async def search(self, params: SearchParameters, force_refresh: bool = False) -> List[RoundTripItinerary]:
        origins = params.origins if params.origins else self.settings.default_home_airports
        ret_date_from = params.date_from + timedelta(days=params.min_nights)
        ret_date_to = params.date_to + timedelta(days=params.max_nights)

        outbound_legs: List[FlightLeg] = []
        inbound_legs: List[FlightLeg] = []

        is_anywhere = params.destination.strip().lower() in ("anywhere", "everywhere", "", "all")
        dest_targets = [d.strip() for d in re.split(r'[,/]', params.destination) if d.strip()] if not is_anywhere else []

        if not force_refresh and not is_anywhere:
            cached_out = self.cache.get_legs(
                origins=origins,
                destinations=dest_targets,
                date_from=params.date_from,
                date_to=params.date_to,
                currency=params.currency,
                airlines=params.airlines,
            )
            cached_in = self.cache.get_legs(
                origins=dest_targets,
                destinations=origins,
                date_from=ret_date_from,
                date_to=ret_date_to,
                currency=params.currency,
                airlines=params.airlines,
            )
            if cached_out and cached_in:
                cached_combos = self.combine_legs(cached_out, cached_in, params)
                if cached_combos:
                    return cached_combos

        # If we need fresh data
        if not outbound_legs or not inbound_legs:
            if is_anywhere:
                # Step 1: Broad multi-origin & country outbound sweep
                outbound_tasks = []
                # Query each home airport individually to avoid 15-result single-call capping
                for orig in origins:
                    outbound_tasks.append(
                        self.provider.get_one_way_fares(
                            origins=orig,
                            destinations="anywhere",
                            date_from=params.date_from,
                            date_to=params.date_to,
                            airlines=params.airlines,
                            currency=params.currency,
                            direct_only=True,
                        )
                    )

                # Also sweep key budget country clusters for maximum destination variety
                for reg in ["IT", "GB", "PL", "DE", "ES", "FR", "AL,MK,GR"]:
                    outbound_tasks.append(
                        self.provider.get_one_way_fares(
                            origins=origins,
                            destinations=reg,
                            date_from=params.date_from,
                            date_to=params.date_to,
                            airlines=params.airlines,
                            currency=params.currency,
                            direct_only=True,
                        )
                    )

                out_results = await asyncio.gather(*outbound_tasks, return_exceptions=True)
                fresh_out: List[FlightLeg] = []
                for r in out_results:
                    if isinstance(r, list):
                        fresh_out.extend(r)

                self.cache.save_legs(fresh_out)
                outbound_legs = fresh_out

                # Extract discovered unique destination airport codes
                dest_codes = list(set(leg.destination for leg in outbound_legs if leg.destination))

                # Step 2: Targeted parallel inbound queries per discovered destination
                if dest_codes:
                    tasks = [
                        self.provider.get_one_way_fares(
                            origins=dest,
                            destinations=origins,
                            date_from=ret_date_from,
                            date_to=ret_date_to,
                            airlines=params.airlines,
                            currency=params.currency,
                            direct_only=True,
                        )
                        for dest in dest_codes
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    fresh_in: List[FlightLeg] = []
                    for res in results:
                        if isinstance(res, list):
                            fresh_in.extend(res)
                    self.cache.save_legs(fresh_in)
                    inbound_legs = fresh_in
            else:
                # Targeted search for specific destination(s) across all home origins
                out_tasks = []
                for orig in origins:
                    for t in dest_targets:
                        out_tasks.append(
                            self.provider.get_one_way_fares(
                                origins=orig,
                                destinations=t,
                                date_from=params.date_from,
                                date_to=params.date_to,
                                airlines=params.airlines,
                                currency=params.currency,
                                direct_only=True,
                            )
                        )
                out_results = await asyncio.gather(*out_tasks, return_exceptions=True)
                fresh_out: List[FlightLeg] = []
                for r in out_results:
                    if isinstance(r, list):
                        fresh_out.extend(r)
                self.cache.save_legs(fresh_out)
                outbound_legs = fresh_out

                # Targeted parallel inbound queries for discovered airport codes + target entities
                dest_codes = list(set(leg.destination for leg in outbound_legs if leg.destination))
                in_targets = list(set(dest_codes + dest_targets))
                if in_targets:
                    in_tasks = [
                        self.provider.get_one_way_fares(
                            origins=t,
                            destinations=origins,
                            date_from=ret_date_from,
                            date_to=ret_date_to,
                            airlines=params.airlines,
                            currency=params.currency,
                            direct_only=True,
                        )
                        for t in in_targets
                    ]
                    in_results = await asyncio.gather(*in_tasks, return_exceptions=True)
                    fresh_in: List[FlightLeg] = []
                    for res in in_results:
                        if isinstance(res, list):
                            fresh_in.extend(res)
                    self.cache.save_legs(fresh_in)
                    inbound_legs = fresh_in

        return self.combine_legs(outbound_legs, inbound_legs, params)

    async def get_explore_destinations(self, params: SearchParameters) -> List[ExploreDestinationSummary]:
        itineraries = await self.search(params)
        dest_map: Dict[str, List[RoundTripItinerary]] = {}

        for it in itineraries:
            dest = it.outbound.destination
            dest_map.setdefault(dest, []).append(it)

        summaries: List[ExploreDestinationSummary] = []
        for dest, items in dest_map.items():
            if not items:
                continue
            cheapest = min(items, key=lambda x: x.total_price)
            routes = list(set(f"{it.outbound.origin}-{it.outbound.destination}" for it in items))
            has_oj = any(it.is_open_jaw for it in items)
            dates_str = f"{cheapest.outbound.departure_date.strftime('%b %d')} - {cheapest.inbound.departure_date.strftime('%b %d')}"

            summaries.append(
                ExploreDestinationSummary(
                    destination_code=dest,
                    city_name=cheapest.destination_city or dest,
                    country_name=cheapest.destination_country,
                    cheapest_price=cheapest.total_price,
                    currency=cheapest.currency,
                    example_dates=dates_str,
                    sample_itinerary_id=cheapest.id,
                    routes_available=routes,
                    is_open_jaw_available=has_oj,
                )
            )

        summaries.sort(key=lambda s: s.cheapest_price)
        return summaries

    async def get_calendar_heatmap(
        self,
        destination: str,
        date_from: date,
        date_to: date,
        min_nights: int = 2,
        max_nights: int = 4,
        origins: Optional[List[str]] = None,
        currency: str = "EUR",
        allow_open_jaw: bool = True,
    ) -> List[HeatmapCell]:
        params = SearchParameters(
            destination=destination,
            origins=origins or self.settings.default_home_airports,
            date_from=date_from,
            date_to=date_to,
            min_nights=min_nights,
            max_nights=max_nights,
            departure_weekdays=[0, 1, 2, 3, 4, 5, 6],  # all days for heatmap
            allow_open_jaw=allow_open_jaw,
            currency=currency,
        )
        itineraries = await self.search(params)

        grid: Dict[Tuple[date, int], RoundTripItinerary] = {}
        for it in itineraries:
            key = (it.outbound.departure_date, it.nights)
            if key not in grid or it.total_price < grid[key].total_price:
                grid[key] = it

        cells: List[HeatmapCell] = []
        cur_date = date_from
        while cur_date <= date_to:
            for n in range(min_nights, max_nights + 1):
                best = grid.get((cur_date, n))
                if best:
                    carriers = f"{best.outbound.carrier_code}+{best.inbound.carrier_code}"
                    cells.append(
                        HeatmapCell(
                            departure_date=cur_date,
                            nights=n,
                            cheapest_price=best.total_price,
                            currency=currency,
                            itinerary_id=best.id,
                            is_open_jaw=best.is_open_jaw,
                            carrier_summary=carriers,
                        )
                    )
                else:
                    cells.append(
                        HeatmapCell(
                            departure_date=cur_date,
                            nights=n,
                            cheapest_price=None,
                            currency=currency,
                        )
                    )
            cur_date += timedelta(days=1)

        return cells
