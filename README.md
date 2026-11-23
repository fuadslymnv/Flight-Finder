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

# Search weekend getaway deals for 9-5 workers
python find.py --weekend-deals

# Using CLI Flags
python find.py --origin BUD,BTS --dest Rome --nights 2-3 --weekdays Fri,Sat --currency EUR
```

---

### 3. Weekend Deal Alert Watcher & Telegram Notifications

Built specifically for travelers working **9-5 on weekdays**:
- **Outbound**: Friday anytime or Saturday anytime.
- **Return**: Sunday anytime or **Monday morning landing before 09:00 AM** (so you can be on time for work!).
- **Horizon**: Next 60 days.
- **Budget**: Deals under **60 EUR** (configurable).
- **Open-Jaw**: Fully supported (e.g., depart BUD, return to BTS or DEB).
- **Schedule**: Scans every **6 hours starting at 9:00 AM** (`09:00`, `15:00`, `21:00`, `03:00`).
- **Smart Deduplication**: Avoids repeated alerts unless a deal is brand new or the price has dropped.

#### Setup Telegram Bot (2 minutes):
1. Open Telegram and search for `@BotFather`. Send `/newbot`, choose a name and username, and copy your **Bot Token**.
2. Open Telegram and search for `@userinfobot`. Send `/start` and copy your numeric **Id** (this is your **Chat ID**).
3. Put them in `settings.json` under `"alerts.telegram"` or in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN="your_token_here"
   TELEGRAM_CHAT_ID="your_chat_id_here"
   ```
4. Verify connection:
   ```bash
   python alert_watcher.py --test-telegram
   ```

#### Run Deal Checks & Watcher:
```bash
# 1. Run an immediate scan now and send deals:
python alert_watcher.py --now

# 2. Run continuous background scheduler (every 6 hours starting from 9:00 AM):
python alert_watcher.py --daemon

# 3. Dry-run mode (find and display deals without sending messages):
python alert_watcher.py --dry-run

# 4. Custom budget override (e.g. under 50 EUR):
python alert_watcher.py --max-price 50
```

---

### 4. Run the Web Application

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
