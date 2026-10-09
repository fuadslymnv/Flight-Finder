from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FlightSegment(BaseModel):
    departure_airport: str
    arrival_airport: str
    departure_city: str = ""
    arrival_city: str = ""
    departure_country: str = ""
    arrival_country: str = ""
    departure_time: datetime
    arrival_time: datetime
    carrier_code: str
    carrier_name: str
    flight_number: str
    duration_seconds: int = 0


class FlightLeg(BaseModel):
    id: str
    origin: str
    destination: str
    origin_city: str = ""
    destination_city: str = ""
    origin_country: str = ""
    destination_country: str = ""
    departure_time: datetime
    arrival_time: datetime
    departure_date: date
    carrier_code: str
    carrier_name: str
    flight_number: str
    price: float
    currency: str = "EUR"
    booking_url: str = ""
    direct_airline_url: str = ""
    duration_seconds: int = 0
    stops: int = 0
    segments: List[FlightSegment] = Field(default_factory=list)


class GroundTransferInfo(BaseModel):
    required: bool = False
    origin_airport: str = ""
    return_airport: str = ""
    transit_hours: float = 0.0
    transit_description: str = ""
    estimated_cost_eur: float = 0.0
    estimated_cost_huf: float = 0.0


class RoundTripItinerary(BaseModel):
    id: str
    outbound: FlightLeg
    inbound: FlightLeg
    nights: int
    is_open_jaw: bool
    ground_transfer: Optional[GroundTransferInfo] = None
    flight_price_total: float
    ground_transfer_cost: float = 0.0
    total_price: float
    currency: str = "EUR"
    destination_city: str = ""
    destination_country: str = ""
    disclaimer: str = "Prices are base fares per leg, luggage/seat selection extra. Each leg is booked separately."


class SearchParameters(BaseModel):
    query_text: Optional[str] = ""
    origins: List[str] = Field(default_factory=lambda: ["BUD", "DEB", "BTS"])
    destination: str = "anywhere"
    date_from: date
    date_to: date
    min_nights: int = 2
    max_nights: int = 3
    departure_weekdays: List[int] = Field(default_factory=lambda: [4, 5])  # 4=Fri, 5=Sat (0=Mon..6=Sun)
    return_weekdays: Optional[List[int]] = None
    allow_open_jaw: bool = True
    include_ground_transfer_cost: bool = False
    max_price: Optional[float] = None
    currency: str = "EUR"
    airlines: List[str] = Field(default_factory=lambda: ["W6", "W9", "FR", "RK"])
    exclude_destinations: List[str] = Field(default_factory=list)
    min_outbound_hour: Optional[int] = None
    thursday_evening_only: bool = False


class GroundTransferPreset(BaseModel):
    route: str  # e.g. "BUD-BTS"
    from_airport: str
    to_airport: str
    transit_hours: float
    description: str
    cost_eur: float
    cost_huf: float


class AppSettings(BaseModel):
    default_home_airports: List[str] = ["BUD", "DEB", "BTS"]
    default_airlines: List[str] = ["W6", "W9", "FR", "RK"]
    default_currency: str = "EUR"
    cache_ttl_hours: int = 4
    include_ground_transfer_cost_by_default: bool = False
    ground_transfers: Dict[str, GroundTransferPreset] = Field(default_factory=dict)


class ExploreDestinationSummary(BaseModel):
    destination_code: str
    city_name: str
    country_name: str
    cheapest_price: float
    currency: str
    example_dates: str
    sample_itinerary_id: str
    routes_available: List[str]  # e.g. ["BUD-STN", "BTS-STN"]
    is_open_jaw_available: bool


class HeatmapCell(BaseModel):
    departure_date: date
    nights: int
    cheapest_price: Optional[float] = None
    currency: str = "EUR"
    itinerary_id: Optional[str] = None
    is_open_jaw: bool = False
    carrier_summary: str = ""
