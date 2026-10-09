# ✈️ Cheap Flight Finder (Wizz Air + Ryanair only)

A personal Google Flights-style flight discovery application built specifically for travelers in the **Budapest (BUD) / Debrecen (DEB) / Bratislava (BTS)** region. It finds the cheapest short trips across **Wizz Air (W6/W9)** and **Ryanair (FR/RK)** with full **Open-Jaw** round-trip pairing (e.g., depart BUD, return BTS).

---

## 🌟 Key Features

1. **Natural Language Search Bar**: Type queries like `"cheap 2-3 night trip, leave Fri or Sat, next 2 months"` and get instant parsed interactive chips.
2. **One-Way Leg Combination Engine**: Combines independent one-way fares locally into round trips and open-jaw routes.
3. **Open-Jaw Support with Ground Transit Estimates**: Clearly flags open-jaw itineraries and includes transit estimates (e.g. BUD $\leftrightarrow$ BTS ~2.5h / ~15 EUR by RegioJet/FlixBus). Includes an optional toggle to factor transit cost directly into price rankings.
4. **Editable Ground Transfer Presets**: Customize duration and transit costs (in EUR and HUF) directly in the UI settings or `settings.json`.
5. **Dual Booking Links**: Direct deep links to Kiwi checkout AND direct booking search links to Ryanair and Wizz Air.
6. **Price Calendar Heatmap**: Interactive departure date $\times$ trip nights matrix color-coded for quick visual discovery.
7. **Explore View**: Grid of cheapest destination cards aggregated from all home airports.
8. **Multi-Currency (EUR & HUF)**: Seamless instant switching between Euro (€) and Hungarian Forint (Ft).
9. **SQLite Caching**: Cached flight legs with configurable TTL (default 4 hours) for sub-millisecond re-filtering with zero extra API requests.

---

## 🏗️ Architecture & Tech Stack

```
FlightFinder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application + static frontend mounting
│   │   └── api/routes.py        # REST API endpoints (parse, search, explore, calendar, settings)
│   ├── core/
│   │   ├── models.py            # Pydantic v2 data models
│   │   ├── provider.py          # FareProvider ABC & airline direct URL generator
│   │   ├── kiwi_provider.py     # Kiwi MCP Streamable HTTP JSON-RPC provider
│   │   ├── combiner.py          # FlightEngine & local Cartesian open-jaw combiner
│   │   ├── cache.py             # SQLite caching engine
│   │   ├── parser.py            # Deterministic rule-based Natural Language parser
│   │   └── settings.py          # Settings & Ground Transfer presets manager
│   └── tests/
│       ├── test_acceptance.py   # Official acceptance test
│       ├── test_api.py          # FastAPI endpoint tests
│       ├── test_cache.py        # SQLite cache tests
│       ├── test_combiner.py     # Combiner & open-jaw logic tests
│       ├── test_parser.py       # Natural language parser tests
│       └── test_scenarios.py    # End-to-end workflow scenarios
├── frontend/                    # React 19 + Vite + Tailwind CSS UI
│   ├── src/
│   │   ├── components/          # Header, SearchBar, FilterChips, FlightCard, ExploreView, CalendarHeatmap, SettingsModal
│   │   ├── App.jsx              # Main app state & tabbed views
│   │   └── api.js               # Frontend API client
│   └── dist/                    # Compiled production build
├── find.py                      # Standalone CLI tool
├── settings.json                # User settings & ground transfer presets
├── requirements.txt             # Python dependencies
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Install Dependencies

#### Python Backend
```bash
pip install -r requirements.txt
```

#### Frontend (Optional for dev, production build is pre-compiled in `frontend/dist`)
```bash
cd frontend
npm install
```

---

### 2. Run the CLI Tool

Search using natural language or explicit flags:

```bash
# Natural Language Search
python find.py "cheap 2-3 night trip, leave Fri or Sat, next 2 months"

# Search with specific constraints
python find.py "BUD to London for 3 nights in November under 80 EUR"

# Using CLI Flags
python find.py --origin BUD,BTS --dest Rome --nights 2-3 --weekdays Fri,Sat --currency EUR
```

---

### 3. Run the Web Application

#### Start the FastAPI Server:
```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser. The backend automatically serves the full React UI!

*(For frontend hot-reload development: run `npm --prefix frontend run dev` and open `http://localhost:5173`)*

---

## 🧪 Running the Test Suite

Execute all 15 unit, acceptance, API, and workflow scenario tests:

```bash
python -m pytest backend/tests -v
```

Tests cover:
- ✅ **Acceptance Test**: Friday/Saturday departures, 2-3 nights, BUD/DEB/BTS origins, W6/FR only, sorted by price.
- ✅ **Combiner & Open-Jaw**: Exact night delta matching, weekday enforcement, open-jaw tagging, and ground transfer cost calculation.
- ✅ **Deterministic NL Parser**: Extraction of nights, weekdays, date horizons, destinations, currencies, and airport filters.
- ✅ **SQLite Cache Acceleration**: Sub-second re-filtering without remote network requests.
- ✅ **FastAPI Endpoints**: Parse, search, explore, calendar, and settings PUT/GET operations.
