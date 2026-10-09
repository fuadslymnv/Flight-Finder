#!/usr/bin/env python3
"""
Cheap Flight Finder CLI (Wizz Air + Ryanair only, BUD / DEB / BTS)
Usage:
    python find.py "cheap 2-3 night trip, leave Fri or Sat, next 2 months"
    python find.py --origin BUD,BTS --dest London --nights 2-3 --weekdays Fri,Sat
"""

import sys
import argparse
import asyncio
from datetime import datetime, date
from pathlib import Path

# Configure utf-8 encoding for standard output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.core.parser import parse_natural_language_query, WEEKDAY_MAP
from backend.core.models import SearchParameters
from backend.core.kiwi_provider import KiwiMcpProvider
from backend.core.combiner import FlightEngine
from backend.core.cache import FlightCache
from backend.core.settings import load_settings

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def format_itinerary_card(idx: int, it, currency: str) -> str:
    out = it.outbound
    ret = it.inbound

    out_day = WEEKDAY_NAMES[out.departure_date.weekday()]
    ret_day = WEEKDAY_NAMES[ret.departure_date.weekday()]

    out_dep_time = out.departure_time.strftime("%H:%M")
    out_arr_time = out.arrival_time.strftime("%H:%M")
    ret_dep_time = ret.departure_time.strftime("%H:%M")
    ret_arr_time = ret.arrival_time.strftime("%H:%M")

    curr_sym = "€" if currency == "EUR" else " Ft"

    lines = []
    lines.append(f"┌─ #{idx:02d} {'[' + it.destination_city.upper() + ']' if it.destination_city else ''} {out.origin} ➔ {out.destination} ➔ {ret.destination} | Total: {it.total_price:,.0f}{curr_sym} ({it.nights} nights)")
    
    if it.is_open_jaw:
        gt = it.ground_transfer
        transit_note = f"⚠️  OPEN-JAW: Out {out.origin}, Return {ret.destination}."
        if gt:
            cost_str = f"~{gt.estimated_cost_eur:.0f}€" if currency == "EUR" else f"~{gt.estimated_cost_huf:,.0f} Ft"
            transit_note += f" Ground transfer ({gt.return_airport}➔{gt.origin_airport}): ~{gt.transit_hours}h ({cost_str}) - {gt.transit_description}"
        lines.append(f"│  {transit_note}")

    out_fl_no = out.flight_number if out.flight_number.startswith(out.carrier_code) else f"{out.carrier_code}{out.flight_number}"
    ret_fl_no = ret.flight_number if ret.flight_number.startswith(ret.carrier_code) else f"{ret.carrier_code}{ret.flight_number}"

    lines.append(f"│  Outbound: {out_day} {out.departure_date.strftime('%d %b %Y')} {out_dep_time} - {out_arr_time} | {out.carrier_name} ({out_fl_no}) | Leg: {out.price:,.0f}{curr_sym}")
    lines.append(f"│  Return:   {ret_day} {ret.departure_date.strftime('%d %b %Y')} {ret_dep_time} - {ret_arr_time} | {ret.carrier_name} ({ret_fl_no}) | Leg: {ret.price:,.0f}{curr_sym}")
    
    if out.booking_url or ret.booking_url:
        lines.append(f"│  Kiwi Links:  Outbound: {out.booking_url or 'N/A'} | Return: {ret.booking_url or 'N/A'}")
    if out.direct_airline_url or ret.direct_airline_url:
        lines.append(f"│  Direct URLs: Outbound: {out.direct_airline_url or 'N/A'}")
        lines.append(f"│               Return:   {ret.direct_airline_url or 'N/A'}")
    lines.append("└" + "─" * 85)
    return "\n".join(lines)


async def async_main():
    parser = argparse.ArgumentParser(description="Cheap Flight Finder (Wizz Air & Ryanair only)")
    parser.add_argument("query", nargs="?", default="", help="Natural language query, e.g. 'cheap 2-3 night trip, leave Fri or Sat'")
    parser.add_argument("--origin", help="Comma-separated origin airports, e.g. BUD,BTS,DEB")
    parser.add_argument("--dest", help="Destination airport or city or 'anywhere'")
    parser.add_argument("--nights", help="Nights range, e.g. 2-3")
    parser.add_argument("--weekdays", help="Outbound weekdays, e.g. Fri,Sat")
    parser.add_argument("--from-date", dest="from_date", help="Date from YYYY-MM-DD")
    parser.add_argument("--to-date", dest="to_date", help="Date to YYYY-MM-DD")
    parser.add_argument("--currency", choices=["EUR", "HUF"], default="EUR", help="Currency")
    parser.add_argument("--max-price", type=float, help="Max total price")
    parser.add_argument("--no-open-jaw", action="store_true", help="Disallow open-jaw roundtrips")
    parser.add_argument("--include-transfer-cost", action="store_true", help="Add ground transfer cost to ranking")
    parser.add_argument("--refresh", action="store_true", help="Force refresh data bypassing cache")
    parser.add_argument("--limit", type=int, default=25, help="Number of results to display")

    args = parser.parse_args()

    # Step 1: Parse natural language query if provided
    if args.query:
        params = parse_natural_language_query(args.query)
        print(f"\n💬 Natural language query: \"{args.query}\"")
    else:
        today = date.today()
        from datetime import timedelta
        params = SearchParameters(
            date_from=today + timedelta(days=7),
            date_to=today + timedelta(days=60),
            currency=args.currency,
        )

    # Step 2: Override with explicit CLI flags if passed
    if args.origin:
        params.origins = [o.strip().upper() for o in args.origin.split(",")]
    if args.dest:
        params.destination = args.dest.strip()
    if args.nights:
        parts = args.nights.split("-")
        params.min_nights = int(parts[0])
        params.max_nights = int(parts[1]) if len(parts) > 1 else int(parts[0])
    if args.weekdays:
        days = []
        for w in args.weekdays.split(","):
            w_clean = w.strip().lower()
            if w_clean in WEEKDAY_MAP:
                days.append(WEEKDAY_MAP[w_clean])
        if days:
            params.departure_weekdays = days
    if args.from_date:
        params.date_from = datetime.strptime(args.from_date, "%Y-%m-%d").date()
    if args.to_date:
        params.date_to = datetime.strptime(args.to_date, "%Y-%m-%d").date()
    if args.currency:
        params.currency = args.currency
    if args.max_price is not None:
        params.max_price = args.max_price
    if args.no_open_jaw:
        params.allow_open_jaw = False
    if args.include_transfer_cost:
        params.include_ground_transfer_cost = True

    days_str = ", ".join(WEEKDAY_NAMES[d] for d in params.departure_weekdays)
    curr_sym = "€" if params.currency == "EUR" else "Ft"

    print("=" * 87)
    print(f"✈️  CHEAP FLIGHT FINDER (Wizz Air & Ryanair only)")
    print("=" * 87)
    print(f"📍 Home Airports:     {', '.join(params.origins)}")
    print(f"🎯 Destination:       {params.destination}")
    print(f"📅 Travel Window:     {params.date_from.strftime('%d %b %Y')} ➔ {params.date_to.strftime('%d %b %Y')}")
    print(f"🌙 Trip Length:       {params.min_nights} - {params.max_nights} nights")
    print(f"🗓️  Outbound Days:     {days_str}")
    print(f"🔄 Open-Jaw Allowed:  {'Yes (Any Home Airport)' if params.allow_open_jaw else 'No (Same Airport Only)'}")
    print(f"💱 Currency:          {params.currency}")
    if params.max_price:
        print(f"💶 Max Price:         {params.max_price:,.0f} {curr_sym}")
    print("-" * 87)
    print("🔍 Searching flights across Wizz Air (W6) and Ryanair (FR)...")

    provider = KiwiMcpProvider()
    cache = FlightCache()
    settings = load_settings()
    engine = FlightEngine(provider=provider, cache=cache, settings=settings)

    itineraries = await engine.search(params, force_refresh=args.refresh)

    if not itineraries:
        print("\n❌ No matching round trips found for these criteria.")
        print("💡 Try broadening your date window, night range, or departure weekdays.")
        return

    print(f"\n🎉 Found {len(itineraries)} matching round trips (showing top {min(args.limit, len(itineraries))}):")
    print("=" * 87)

    for i, it in enumerate(itineraries[:args.limit], 1):
        print(format_itinerary_card(i, it, params.currency))

    print("\nℹ️  DISCLAIMER:")
    print("• Prices shown are base fares per leg. Luggage, seat selection, and extras are additional.")
    print("• Each one-way leg is booked separately directly with the airline or via Kiwi.")
    print("• Open-jaw trips depart from one home airport and return to another; check ground transfer times.")


def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nSearch cancelled.")


if __name__ == "__main__":
    main()
