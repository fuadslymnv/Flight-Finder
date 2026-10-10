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


def test_parser_advanced_suggestions():
    base = date(2026, 10, 3)
    p1 = parse_natural_language_query("weekend in London in Nov", base_date=base)
    assert p1.destination == "London"
    assert p1.min_nights == 2
    assert p1.max_nights == 3
    assert p1.date_from.month == 11
    assert p1.date_to.month == 11

    p2 = parse_natural_language_query("Milan or Rome under 50 EUR", base_date=base)
    assert "Milan" in p2.destination and "Rome" in p2.destination
    assert p2.max_price == 50.0

    p3 = parse_natural_language_query("Paris for 3 nights", base_date=base)
    assert p3.destination == "Paris"
    assert p3.min_nights == 3
    assert p3.max_nights == 3


def test_parser_any_airport():
    base = date(2026, 10, 3)
    p1 = parse_natural_language_query("from BER to Rome under 50 EUR", base_date=base)
    assert p1.origins == ["BER"]
    assert p1.destination == "Rome"

    p2 = parse_natural_language_query("flights from Vienna to London next month", base_date=base)
    assert "VIE" in p2.origins
    assert p2.destination == "London"

    p3 = parse_natural_language_query("from STN, LTN to Barcelona for weekend", base_date=base)
    assert "STN" in p3.origins and "LTN" in p3.origins
    assert p3.destination == "Barcelona"

    p4 = parse_natural_language_query("from Vilnius to Tallinn for 3 nights", base_date=base)
    assert p4.origins == ["VNO"]
    assert p4.destination == "Tallinn"
    assert p4.min_nights == 3


