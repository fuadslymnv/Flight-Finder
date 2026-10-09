import json
from pathlib import Path
from typing import Dict
from backend.core.models import AppSettings, GroundTransferPreset

DEFAULT_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "settings.json"

DEFAULT_GROUND_TRANSFERS: Dict[str, GroundTransferPreset] = {
    "BUD-BTS": GroundTransferPreset(
        route="BUD-BTS",
        from_airport="BUD",
        to_airport="BTS",
        transit_hours=2.5,
        description="RegioJet / FlixBus between Budapest & Bratislava (frequent departures, ~2.5 hours)",
        cost_eur=15.0,
        cost_huf=6000.0,
    ),
    "BTS-BUD": GroundTransferPreset(
        route="BTS-BUD",
        from_airport="BTS",
        to_airport="BUD",
        transit_hours=2.5,
        description="RegioJet / FlixBus between Bratislava & Budapest (frequent departures, ~2.5 hours)",
        cost_eur=15.0,
        cost_huf=6000.0,
    ),
    "BUD-DEB": GroundTransferPreset(
        route="BUD-DEB",
        from_airport="BUD",
        to_airport="DEB",
        transit_hours=3.0,
        description="MÁV InterCity train between Budapest & Debrecen (~2.5 - 3.0 hours)",
        cost_eur=10.0,
        cost_huf=4000.0,
    ),
    "DEB-BUD": GroundTransferPreset(
        route="DEB-BUD",
        from_airport="DEB",
        to_airport="BUD",
        transit_hours=3.0,
        description="MÁV InterCity train between Debrecen & Budapest (~2.5 - 3.0 hours)",
        cost_eur=10.0,
        cost_huf=4000.0,
    ),
    "DEB-BTS": GroundTransferPreset(
        route="DEB-BTS",
        from_airport="DEB",
        to_airport="BTS",
        transit_hours=5.0,
        description="Train/bus via Budapest connection (~5.0 hours)",
        cost_eur=25.0,
        cost_huf=10000.0,
    ),
    "BTS-DEB": GroundTransferPreset(
        route="BTS-DEB",
        from_airport="BTS",
        to_airport="DEB",
        transit_hours=5.0,
        description="Train/bus via Budapest connection (~5.0 hours)",
        cost_eur=25.0,
        cost_huf=10000.0,
    ),
    "VIE-BTS": GroundTransferPreset(
        route="VIE-BTS",
        from_airport="VIE",
        to_airport="BTS",
        transit_hours=1.0,
        description="Slovak Lines / RegioJet / FlixBus between Vienna & Bratislava (~45-60 mins)",
        cost_eur=8.0,
        cost_huf=3200.0,
    ),
    "BTS-VIE": GroundTransferPreset(
        route="BTS-VIE",
        from_airport="BTS",
        to_airport="VIE",
        transit_hours=1.0,
        description="Slovak Lines / RegioJet / FlixBus between Bratislava & Vienna (~45-60 mins)",
        cost_eur=8.0,
        cost_huf=3200.0,
    ),
    "BUD-VIE": GroundTransferPreset(
        route="BUD-VIE",
        from_airport="BUD",
        to_airport="VIE",
        transit_hours=2.5,
        description="ÖBB Railjet / RegioJet / FlixBus between Budapest & Vienna (~2.5 hours)",
        cost_eur=18.0,
        cost_huf=7200.0,
    ),
    "VIE-BUD": GroundTransferPreset(
        route="VIE-BUD",
        from_airport="VIE",
        to_airport="BUD",
        transit_hours=2.5,
        description="ÖBB Railjet / RegioJet / FlixBus between Vienna & Budapest (~2.5 hours)",
        cost_eur=18.0,
        cost_huf=7200.0,
    ),
}


def load_settings(file_path: Path = DEFAULT_SETTINGS_FILE) -> AppSettings:
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppSettings.model_validate(data)
        except Exception:
            pass
    settings = AppSettings(ground_transfers=DEFAULT_GROUND_TRANSFERS)
    save_settings(settings, file_path)
    return settings


def save_settings(settings: AppSettings, file_path: Path = DEFAULT_SETTINGS_FILE) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(settings.model_dump(), f, indent=2)
