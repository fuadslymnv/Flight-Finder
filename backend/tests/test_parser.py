from datetime import date
from backend.core.parser import parse_natural_language_query


def test_parser_standard_prompt():
    base = date(2026, 10, 3)
    p = parse_natural_language_query("cheap 2-3 night trip, leave Fri or Sat, next 3 months", base_date=base)
    assert p.min_nights == 2
    assert p.max_nights == 3
    assert set(p.departure_weekdays) == {4, 5}  # Fri, Sat
    assert p.currency == "EUR"
    assert p.allow_open_jaw is True
    assert p.destination == "anywhere"
    assert set(p.origins) == {"BUD", "DEB", "BTS"}
    assert (p.date_to - p.date_from).days >= 60


def test_parser_specific_destination_and_currency():
    base = date(2026, 10, 3)
    p = parse_natural_language_query("Budapest to London for 4 nights under 30000 HUF", base_date=base)
    assert p.min_nights == 4
    assert p.max_nights == 4
    assert p.currency == "HUF"
    assert p.max_price == 30000.0
    assert "BUD" in p.origins
    assert "London" in p.destination


def test_parser_same_airport_only():
    base = date(2026, 10, 3)
    p = parse_natural_language_query("weekend trip from BTS, same airport only, under 100 EUR", base_date=base)
    assert p.min_nights == 2
    assert p.max_nights == 3
    assert p.allow_open_jaw is False
    assert p.origins == ["BTS"]
    assert p.max_price == 100.0
