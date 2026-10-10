import re
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from backend.core.models import SearchParameters


MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

WEEKDAY_MAP = {
    "mon": 0, "monday": 0, "mondays": 0,
    "tue": 1, "tues": 1, "tuesday": 1, "tuesdays": 1,
    "wed": 2, "wednesday": 2, "wednesdays": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "thursdays": 3,
    "fri": 4, "friday": 4, "fridays": 4,
    "sat": 5, "saturday": 5, "saturdays": 5,
    "sun": 6, "sunday": 6, "sundays": 6,
}

AIRPORT_KEYWORDS = {
    "bud": "BUD", "budapest": "BUD",
    "deb": "DEB", "debrecen": "DEB",
    "bts": "BTS", "bratislava": "BTS",
    "vie": "VIE", "vienna": "VIE", "wien": "VIE",
}


def parse_natural_language_query(text: str, base_date: Optional[date] = None) -> SearchParameters:
    today = base_date or date.today()
    q = text.lower().strip()

    # 1. Parse Nights
    min_nights, max_nights = 2, 3  # default
    night_range_match = re.search(r'(\d+)\s*(?:-|to)\s*(\d+)\s*nights?', q)
    if night_range_match:
        min_nights = int(night_range_match.group(1))
        max_nights = int(night_range_match.group(2))
    else:
        single_night_match = re.search(r'(\d+)\s*nights?', q)
        if single_night_match:
            min_nights = int(single_night_match.group(1))
            max_nights = min_nights
        elif "long weekend" in q:
            min_nights, max_nights = 3, 4
        elif "weekend" in q:
            min_nights, max_nights = 2, 3

    # 2. Parse Weekdays
    departure_weekdays: List[int] = []
    if "weekend" in q:
        departure_weekdays = [4, 5]  # Friday, Saturday

    for name, idx in WEEKDAY_MAP.items():
        if re.search(rf'\b{name}\b', q):
            if idx not in departure_weekdays:
                departure_weekdays.append(idx)

    # If nothing specified, default to Friday and Saturday for weekend/short trips
    if not departure_weekdays:
        departure_weekdays = [4, 5]

    departure_weekdays.sort()

    # 3. Parse Date Horizon
    date_from = today + timedelta(days=7)  # default start 1 week out
    date_to = today + timedelta(days=90)   # default end 3 months out

    days_ahead_match = re.search(r'next\s+(\d+)\s+days?', q)
    months_ahead_match = re.search(r'next\s+(\d+)\s+months?', q)
    
    if days_ahead_match:
        d_count = int(days_ahead_match.group(1))
        date_from = today + timedelta(days=1)
        date_to = today + timedelta(days=d_count)
    elif months_ahead_match:
        m_count = int(months_ahead_match.group(1))
        date_from = today + timedelta(days=7)
        date_to = today + timedelta(days=m_count * 30)
    elif "next month" in q:
        date_from = today + timedelta(days=7)
        date_to = today + timedelta(days=35)
    elif "next 2 months" in q:
        date_from = today + timedelta(days=7)
        date_to = today + timedelta(days=60)
    elif "next 3 months" in q:
        date_from = today + timedelta(days=7)
        date_to = today + timedelta(days=90)
    else:
        # Check specific month mention, e.g. "in november", "in dec"
        month_found = None
        for m_name, m_num in MONTH_NAMES.items():
            if re.search(rf'\b(?:in|for|during)\s+{m_name}\b', q):
                month_found = m_num
                break
        if month_found:
            year = today.year
            if month_found < today.month:
                year += 1
            # Start from the 1st of that month (or today + 1 if current month)
            start_d = date(year, month_found, 1)
            if start_d < today:
                start_d = today + timedelta(days=1)
            # End of month
            if month_found in (1, 3, 5, 7, 8, 10, 12):
                end_day = 31
            elif month_found == 2:
                end_day = 28
            else:
                end_day = 30
            date_from = start_d
            date_to = date(year, month_found, end_day)

    # 4. Parse Currency & Max Price
    currency = "EUR"
    if "huf" in q or "ft" in q or "forint" in q:
        currency = "HUF"
    elif "eur" in q or "€" in q or "euro" in q:
        currency = "EUR"

    max_price = None
    price_match = re.search(r'(?:under|max|less than|up to|<)\s*(\d+(?:[.,]\d+)?)\s*(?:eur|€|huf|ft|euro|k\s*huf|k\s*ft)?', q)
    if price_match:
        val = float(price_match.group(1).replace(",", "."))
        if "k" in q[price_match.start():price_match.end() + 5]:
            val *= 1000
        max_price = val

    # 5. Parse Origins
    origins = []
    from_match = re.search(r'from\s+([a-zA-Z\s,]+?)(?:\s+to|\s+for|\s+in|\s+under|\s+next|\s+exclude|$)', q)
    if from_match:
        from_text = from_match.group(1)
        for word, code in AIRPORT_KEYWORDS.items():
            if word in from_text and code not in origins:
                origins.append(code)
    else:
        for word, code in AIRPORT_KEYWORDS.items():
            if re.search(rf'\b{word}\b', q) and code not in origins:
                origins.append(code)

    if not origins:
        origins = ["BUD", "DEB", "BTS"]

    # 6. Parse Exclusions (e.g. "exclude Warsaw, London, Milan")
    exclude_destinations = []
    excl_match = re.search(r'(?:exclude|excluding|except|without)\s+([a-zA-Z\s,]+?)(?:\s+in|\s+under|\s+next|\s+for|\s+departing|$)', q)
    if excl_match:
        raw_excl = excl_match.group(1)
        parts = re.split(r'[,/]|(?:\band\b)', raw_excl)
        for p in parts:
            item = p.strip()
            if item and len(item) > 1 and item.lower() not in {"the", "a", "from", "to"}:
                exclude_destinations.append(item.title())

    # 7. Parse Destination
    destination = "anywhere"
    delimiters = [
        r'next\s+(?:month|months|days|weeks|weekend|year|\d+)',
        r'in\s+(?:the\s+)?next',
        r'in\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|april|may|june|july|august|september|october|november|december)',
        r'for\s+\d+\s*(?:to|-)?\s*\d*\s*nights?',
        r'\d+\s*(?:to|-)?\s*\d*\s*nights?',
        r'under\s+\d+',
        r'less\s+than\s+\d+',
        r'up\s+to\s+\d+',
        r'max\s+\d+',
        r'leave|leaving|departing|depart',
        r'exclude|excluding|except|without',
        r'same\s+airport|open\s+jaw|no\s+open\s+jaw',
        r'from\s+[a-zA-Z\s,]+',
    ]
    delim_pattern = "|".join(delimiters)

    stop_dest_words = {
        "a", "the", "any", "cheap", "anywhere", "europe", "places", "destinations",
        "somewhere", "trip", "trips", "flight", "flights", "weekend", "long weekend",
        "vacation", "holiday", "leave", "leaving", "depart", "departing", "go", "going",
        "fly", "flying", "travel", "traveling"
    }
    time_dest_words = set(MONTH_NAMES.keys()) | {
        "next", "in", "at", "for", "summer", "winter", "spring", "fall", "autumn",
        "today", "tomorrow", "month", "months", "year", "week", "weeks", "days", "day"
    }

    def _clean_destination_candidate(raw: str) -> Optional[str]:
        parts = re.split(r'[,/]|(?:\b(?:and|or)\b)', raw)
        cleaned_list = []
        for p in parts:
            words = [
                w for w in p.strip().split()
                if w.lower() not in stop_dest_words and w.lower() not in time_dest_words
            ]
            if words:
                d_str = " ".join(words).title()
                if d_str.lower() in ("tallin", "talinn"):
                    d_str = "Tallinn"
                if d_str.lower() not in AIRPORT_KEYWORDS:
                    cleaned_list.append(d_str)
        return ", ".join(cleaned_list) if cleaned_list else None

    # Try explicit 'to / visiting / towards'
    to_match = re.search(
        rf'(?:to|visiting|towards)\s+([a-zA-Z0-9\s,/\-]+?)(?=\s+(?:{delim_pattern})|$)',
        q,
        re.IGNORECASE
    )
    if to_match:
        cand = _clean_destination_candidate(to_match.group(1).strip())
        if cand:
            destination = cand

    # If still 'anywhere', try 'in / at <destination>'
    if destination == "anywhere":
        in_matches = re.finditer(
            rf'(?:in|at)\s+([a-zA-Z0-9\s,/\-]+?)(?=\s+(?:{delim_pattern})|$)',
            q,
            re.IGNORECASE
        )
        for m in in_matches:
            cand = _clean_destination_candidate(m.group(1).strip())
            if cand:
                destination = cand
                break

    # If still 'anywhere', check leading destination (e.g. 'Milan or Rome under 50 EUR', 'Paris for 3 nights')
    if destination == "anywhere":
        lead_match = re.search(
            rf'^([a-zA-Z0-9\s,/\-]+?)(?=\s+(?:{delim_pattern})|$)',
            q,
            re.IGNORECASE
        )
        if lead_match:
            cand = _clean_destination_candidate(lead_match.group(1).strip())
            if cand:
                destination = cand

    # 8. Parse Open-Jaw preference
    allow_open_jaw = True
    if "same airport only" in q or "no open jaw" in q or "same origin" in q:
        allow_open_jaw = False
    elif "open jaw" in q or "open-jaw" in q:
        allow_open_jaw = True

    # 9. Time of day (e.g. "Thursday evening")
    thursday_evening_only = "thursday evening" in q or ("evening" in q and 3 in departure_weekdays)
    min_outbound_hour = 17 if "evening" in q else None

    return SearchParameters(
        query_text=text,
        origins=origins,
        destination=destination,
        date_from=date_from,
        date_to=date_to,
        min_nights=min_nights,
        max_nights=max_nights,
        departure_weekdays=departure_weekdays,
        allow_open_jaw=allow_open_jaw,
        max_price=max_price,
        currency=currency,
        airlines=["W6", "W9", "FR", "RK"],
        exclude_destinations=exclude_destinations,
        min_outbound_hour=min_outbound_hour,
        thursday_evening_only=thursday_evening_only,
    )
