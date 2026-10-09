import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import FilterChips from './components/FilterChips';
import FlightCard from './components/FlightCard';
import ExploreView from './components/ExploreView';
import CalendarHeatmap from './components/CalendarHeatmap';
import SettingsModal from './components/SettingsModal';
import { parseQuery, searchFlights, exploreDestinations, clearCache } from './api';
import { 
  Plane, 
  Compass, 
  Calendar as CalendarIcon, 
  ArrowUpDown, 
  RotateCcw, 
  Info,
  Loader2,
  AlertCircle
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('results'); // 'results' | 'explore' | 'calendar'
  const [currency, setCurrency] = useState('EUR');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [itineraries, setItineraries] = useState([]);
  const [exploreData, setExploreData] = useState([]);
  const [sortBy, setSortBy] = useState('price'); // 'price' | 'date' | 'nights'
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [notification, setNotification] = useState('');

  // Search parameters state
  const [params, setParams] = useState({
    query_text: "cheap 2-3 night trip, leave Fri or Sat, next 2 months",
    origins: ["BUD", "DEB", "BTS"],
    destination: "anywhere",
    date_from: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0],
    date_to: new Date(Date.now() + 60 * 86400000).toISOString().split('T')[0],
    min_nights: 2,
    max_nights: 3,
    departure_weekdays: [4, 5], // Fri, Sat
    allow_open_jaw: true,
    include_ground_transfer_cost: false,
    max_price: null,
    currency: "EUR",
    airlines: ["W6", "W9", "FR", "RK"],
  });

  // Initial load
  useEffect(() => {
    handleSearch(params);
  }, []);

  // Update currency when changed in header
  const handleCurrencyChange = (newCurr) => {
    setCurrency(newCurr);
    const updated = { ...params, currency: newCurr };
    setParams(updated);
    handleSearch(updated);
  };

  const handleParseAndSearch = async (queryText) => {
    setLoading(true);
    setError(null);
    try {
      const parsed = await parseQuery(queryText);
      const merged = { ...parsed, currency };
      setParams(merged);
      await handleSearch(merged);
    } catch (err) {
      console.error('Parse error:', err);
      setError('Could not parse query. Please try adjusting your search terms.');
      setLoading(false);
    }
  };

  const handleSearch = async (currentParams = params, forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await searchFlights(currentParams, forceRefresh);
      setItineraries(res.itineraries || []);
      
      // Also fetch explore summary if in anywhere mode
      if (currentParams.destination === 'anywhere' || !currentParams.destination) {
        exploreDestinations(currentParams).then(setExploreData).catch(() => {});
      }
    } catch (err) {
      console.error('Search error:', err);
      setError('Search failed. Please check backend connection or try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await clearCache();
      showToast('Cache cleared! Fetching fresh flight data...');
      handleSearch(params, true);
    } catch (err) {
      console.error('Clear cache error:', err);
    }
  };

  const showToast = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(''), 4000);
  };

  const handleExploreSelect = (destCode) => {
    const updated = { ...params, destination: destCode };
    setParams(updated);
    setActiveTab('results');
    handleSearch(updated);
  };

  // Sort itineraries
  const sortedItineraries = [...itineraries].sort((a, b) => {
    if (sortBy === 'price') return a.total_price - b.total_price;
    if (sortBy === 'date') return new Date(a.outbound.departure_time) - new Date(b.outbound.departure_time);
    if (sortBy === 'nights') return a.nights - b.nights;
    return 0;
  });

  return (
    <div className="min-h-screen bg-[#f8fafd] flex flex-col justify-between">
      <div>
        <Header
          currency={currency}
          setCurrency={handleCurrencyChange}
          onOpenSettings={() => setSettingsOpen(true)}
          onClearCache={handleClearCache}
        />

        {/* Notification Toast */}
        {notification && (
          <div className="max-w-md mx-auto mt-4 px-4 py-2.5 bg-gray-900 text-white text-xs font-semibold rounded-xl shadow-lg flex items-center justify-between animate-fade-in">
            <span>{notification}</span>
            <button onClick={() => setNotification('')} className="ml-3 text-gray-400 hover:text-white">✕</button>
          </div>
        )}

        {/* Hero Search Section */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 sm:pt-8 pb-6">
          <div className="text-center max-w-3xl mx-auto mb-6 sm:mb-8">
            <h1 className="text-2xl sm:text-4xl font-extrabold text-gray-900 tracking-tight">
              Cheap Flights from <span className="text-blue-600">Budapest</span>, <span className="text-blue-600">Debrecen</span> & <span className="text-blue-600">Bratislava</span>
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 font-medium mt-2">
              Google Flights-style one-way combination engine for Wizz Air & Ryanair with Open-Jaw support.
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-4xl mx-auto mb-6">
            <SearchBar onParseAndSearch={handleParseAndSearch} loading={loading} />
          </div>

          {/* Interactive Chips Bar */}
          <div className="max-w-5xl mx-auto">
            <FilterChips
              params={params}
              onChange={setParams}
              onApply={() => handleSearch(params, false)}
            />
          </div>

          {/* Navigation Tabs */}
          <div className="max-w-5xl mx-auto flex items-center justify-between border-b border-gray-200 pb-3 mb-6">
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setActiveTab('results')}
                className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === 'results'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Plane className="w-3.5 h-3.5" />
                <span>Flight Results ({itineraries.length})</span>
              </button>

              <button
                onClick={() => setActiveTab('explore')}
                className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === 'explore'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <Compass className="w-3.5 h-3.5" />
                <span>Explore Destinations</span>
              </button>

              <button
                onClick={() => setActiveTab('calendar')}
                className={`flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                  activeTab === 'calendar'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                }`}
              >
                <CalendarIcon className="w-3.5 h-3.5" />
                <span>Price Calendar</span>
              </button>
            </div>

            {/* Sort Dropdown (for results tab) */}
            {activeTab === 'results' && itineraries.length > 0 && (
              <div className="flex items-center space-x-1.5 text-xs text-gray-500">
                <ArrowUpDown className="w-3.5 h-3.5" />
                <span className="font-medium hidden sm:inline">Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-transparent font-bold text-gray-800 focus:outline-none cursor-pointer"
                >
                  <option value="price">Cheapest Total Price</option>
                  <option value="date">Earliest Departure Date</option>
                  <option value="nights">Shortest Stay (Nights)</option>
                </select>
              </div>
            )}
          </div>

          {/* Tab Content */}
          <div className="max-w-5xl mx-auto">
            {error && (
              <div className="mb-6 p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                <span>{error}</span>
              </div>
            )}

            {/* RESULTS TAB */}
            {activeTab === 'results' && (
              <div>
                {loading ? (
                  <div className="py-20 text-center">
                    <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
                    <h3 className="text-sm font-bold text-gray-900">Finding cheapest round trips...</h3>
                    <p className="text-xs text-gray-500 mt-1">
                      Querying Wizz Air & Ryanair direct one-way legs across BUD, DEB, and BTS
                    </p>
                  </div>
                ) : sortedItineraries.length === 0 ? (
                  <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
                    <Plane className="w-12 h-12 text-gray-300 mx-auto mb-3 -rotate-45" />
                    <h3 className="text-base font-bold text-gray-900 mb-1">No matching flights found</h3>
                    <p className="text-xs text-gray-500 max-w-md mx-auto mb-4">
                      Try expanding your departure weekdays, night range, or date window.
                    </p>
                    <button
                      onClick={() => {
                        const reset = {
                          ...params,
                          departure_weekdays: [4, 5],
                          min_nights: 2,
                          max_nights: 4,
                          destination: 'anywhere',
                        };
                        setParams(reset);
                        handleSearch(reset);
                      }}
                      className="px-4 py-2 text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-colors cursor-pointer"
                    >
                      Reset to Weekend Trip
                    </button>
                  </div>
                ) : (
                  <div>
                    {sortedItineraries.map((it, idx) => (
                      <FlightCard key={it.id} itinerary={it} index={idx + 1} />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* EXPLORE TAB */}
            {activeTab === 'explore' && (
              <ExploreView
                destinations={exploreData}
                loading={loading}
                onSelectDestination={handleExploreSelect}
              />
            )}

            {/* CALENDAR TAB */}
            {activeTab === 'calendar' && (
              <CalendarHeatmap
                destination={params.destination}
                params={params}
                currency={currency}
                onSelectDate={(dateStr, nights) => {
                  setParams({
                    ...params,
                    date_from: dateStr,
                    date_to: dateStr,
                    min_nights: nights,
                    max_nights: nights,
                  });
                  setActiveTab('results');
                  handleSearch({
                    ...params,
                    date_from: dateStr,
                    date_to: dateStr,
                    min_nights: nights,
                    max_nights: nights,
                  });
                }}
              />
            )}
          </div>
        </div>
      </div>

      {/* Honest Disclaimer Footer */}
      <footer className="bg-white border-t border-gray-200 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-xs text-gray-500 space-y-2">
          <div className="flex items-center justify-center space-x-1 text-gray-700 font-semibold">
            <Info className="w-3.5 h-3.5 text-blue-600" />
            <span>Honest Fare Transparency</span>
          </div>
          <p className="max-w-3xl mx-auto">
            Prices displayed are base fares per leg and do not include optional luggage or seat selection.
            Each one-way leg is booked independently with Wizz Air or Ryanair.
            Kiwi booking links are provided for convenience, alongside direct airline booking links.
          </p>
          <p className="text-[11px] text-gray-400">
            Cheap Flight Finder • BUD / DEB / BTS Open-Jaw Combinator
          </p>
        </div>
      </footer>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
    </div>
  );
}
