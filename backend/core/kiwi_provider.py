import asyncio
import logging
from datetime import date, datetime
from typing import List, Union, Optional, Dict, Any
import httpx

from backend.core.models import FlightLeg, FlightSegment
from backend.core.provider import FareProvider, build_direct_airline_url

logger = logging.getLogger(__name__)

KIWI_MCP_URL = "https://mcp.kiwi.com/"


class KiwiMcpProvider(FareProvider):
    def __init__(self, endpoint_url: str = KIWI_MCP_URL, timeout_seconds: float = 25.0):
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(3)

    def _format_date(self, d: date) -> str:
        return d.strftime("%d/%m/%Y")

    def _parse_datetime(self, dt_str: Optional[str]) -> datetime:
        if not dt_str:
            return datetime.now()
        # dt_str format like "2026-10-20T05:45:00"
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            return datetime.now()

    def _parse_itinerary_to_leg(self, item: Dict[str, Any], currency: str) -> Optional[FlightLeg]:
        try:
            item_id = item.get("id") or f"kiwi_{item.get('price')}_{item.get('outbound', {}).get('from')}"
            outbound = item.get("outbound", {})
            segments_raw = outbound.get("segments", [])

            if not segments_raw:
                return None

            first_seg = segments_raw[0]
            last_seg = segments_raw[-1]

            origin = outbound.get("from") or first_seg.get("from") or ""
            destination = outbound.get("to") or last_seg.get("to") or ""

            dep_dt = self._parse_datetime(outbound.get("departureTime") or first_seg.get("departureTime"))
            arr_dt = self._parse_datetime(outbound.get("arrivalTime") or last_seg.get("arrivalTime"))

            carrier_code = first_seg.get("carrier") or ""
            carrier_name = first_seg.get("carrierName") or carrier_code
            flight_number = first_seg.get("flightNumber") or ""

            price = float(item.get("price", 0.0))
            booking_url = item.get("bookingUrl") or ""
            direct_url = build_direct_airline_url(carrier_code, origin, destination, dep_dt.date())

            segments: List[FlightSegment] = []
            for seg in segments_raw:
                seg_dep = self._parse_datetime(seg.get("departureTime"))
                seg_arr = self._parse_datetime(seg.get("arrivalTime"))
                segments.append(
                    FlightSegment(
                        departure_airport=seg.get("from") or "",
                        arrival_airport=seg.get("to") or "",
                        departure_city=seg.get("fromCity") or "",
                        arrival_city=seg.get("toCity") or "",
                        departure_country=seg.get("fromCountry") or "",
                        arrival_country=seg.get("toCountry") or "",
                        departure_time=seg_dep,
                        arrival_time=seg_arr,
                        carrier_code=seg.get("carrier") or "",
                        carrier_name=seg.get("carrierName") or "",
                        flight_number=seg.get("flightNumber") or "",
                        duration_seconds=seg.get("durationSeconds") or 0,
                    )
                )

            return FlightLeg(
                id=item_id,
                origin=origin,
                destination=destination,
                origin_city=first_seg.get("fromCity") or "",
                destination_city=last_seg.get("toCity") or "",
                origin_country=first_seg.get("fromCountry") or "",
                destination_country=last_seg.get("toCountry") or "",
                departure_time=dep_dt,
                arrival_time=arr_dt,
                departure_date=dep_dt.date(),
                carrier_code=carrier_code,
                carrier_name=carrier_name,
                flight_number=flight_number,
                price=price,
                currency=currency,
                booking_url=booking_url,
                direct_airline_url=direct_url,
                duration_seconds=outbound.get("durationSeconds") or item.get("totalDurationSeconds") or 0,
                stops=outbound.get("stops", 0),
                segments=segments,
            )
        except Exception as e:
            logger.warning(f"Failed to parse Kiwi itinerary: {e}")
            return None

    async def _call_mcp_search(self, args: Dict[str, Any], max_retries: int = 4) -> List[Dict[str, Any]]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search-flight",
                "arguments": args
            }
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "FlightFinder/1.0"
        }

        async with self._semaphore:
            for attempt in range(max_retries + 1):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        resp = await client.post(self.endpoint_url, json=payload, headers=headers)
                        if resp.status_code in (502, 503, 504, 429):
                            if attempt < max_retries:
                                wait_time = 1.0 * (1.8 ** attempt)
                                logger.info(f"Kiwi MCP transient upstream error ({resp.status_code}), retrying in {wait_time:.1f}s (attempt {attempt+1}/{max_retries})...")
                                await asyncio.sleep(wait_time)
                                continue
                            logger.warning(f"Kiwi MCP request failed after {max_retries} retries with status {resp.status_code}")
                            return []
                        elif resp.status_code != 200:
                            logger.warning(f"Kiwi MCP unexpected status {resp.status_code}: {resp.text[:150]}")
                            return []

                        content = resp.text
                        data = None
                        for line in content.splitlines():
                            if line.startswith("data: "):
                                import json
                                data = json.loads(line[6:])
                                break
                        if not data:
                            import json
                            data = json.loads(content)

                        structured = data.get("result", {}).get("structuredContent", {})
                        itineraries = structured.get("itineraries", [])
                        return itineraries
                except Exception as e:
                    if attempt < max_retries:
                        wait_time = 1.0 * (1.8 ** attempt)
                        logger.info(f"Kiwi MCP connection exception ({e}), retrying in {wait_time:.1f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"Kiwi MCP connection failed: {e}")
                        return []
            return []

    async def get_one_way_fares(
        self,
        origins: Union[List[str], str],
        destinations: Union[List[str], str],
        date_from: date,
        date_to: date,
        airlines: Optional[List[str]] = None,
        currency: str = "EUR",
        direct_only: bool = True,
    ) -> List[FlightLeg]:
        origin_str = ",".join(origins) if isinstance(origins, list) else origins
        dest_str = ",".join(destinations) if isinstance(destinations, list) else destinations

        args: Dict[str, Any] = {
            "flyFrom": origin_str,
            "flyTo": dest_str,
            "departureDate": self._format_date(date_from),
            "departureDateTo": self._format_date(date_to),
            "currency": currency,
        }

        if airlines:
            args["select_airlines"] = ",".join(airlines)

        if direct_only:
            args["max_sector_stopovers"] = 0

        raw_itineraries = await self._call_mcp_search(args)
        legs: List[FlightLeg] = []
        for raw in raw_itineraries:
            leg = self._parse_itinerary_to_leg(raw, currency)
            if leg:
                # Enforce airline filter strictly if specified
                if airlines and leg.carrier_code.upper() not in [a.upper() for a in airlines]:
                    continue
                legs.append(leg)

        return legs
