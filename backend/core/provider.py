from abc import ABC, abstractmethod
from datetime import date
from typing import List, Union, Optional
from backend.core.models import FlightLeg


def build_direct_airline_url(carrier_code: str, origin: str, destination: str, dep_date: date) -> str:
    carrier_upper = (carrier_code or "").upper()
    date_iso = dep_date.strftime("%Y-%m-%d")
    if carrier_upper in ("FR", "RK"):
        # Ryanair
        return f"https://www.ryanair.com/gb/en/trip/flights/select?originIata={origin}&destinationIata={destination}&tpAdults=1&tpStartDate={date_iso}&tpIsReturn=false"
    elif carrier_upper in ("W6", "W9"):
        # Wizz Air
        return f"https://wizzair.com/en-gb/booking/select-flight/{origin}/{dest_safe(destination)}/{date_iso}/null/1/0/0/null"
    return ""


def dest_safe(dest: str) -> str:
    # If destination is a city code or specific airport
    return dest.split(",")[0].strip()


class FareProvider(ABC):
    @abstractmethod
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
        """Fetch one-way flight legs for the given origins, destinations and date range."""
        pass
