import React, { useState } from 'react';
import { 
  MapPin, 
  Calendar as CalendarIcon, 
  Moon, 
  Layers, 
  RotateCw, 
  SlidersHorizontal,
  Bus,
  Check,
  ChevronDown
} from 'lucide-react';

const WEEKDAYS = [
  { id: 0, label: 'Mon' },
  { id: 1, label: 'Tue' },
  { id: 2, label: 'Wed' },
  { id: 3, label: 'Thu' },
  { id: 4, label: 'Fri' },
  { id: 5, label: 'Sat' },
  { id: 6, label: 'Sun' },
];

const POPULAR_AIRPORTS = [
  { code: 'BUD', name: 'Budapest' },
  { code: 'BTS', name: 'Bratislava' },
  { code: 'VIE', name: 'Vienna' },
  { code: 'DEB', name: 'Debrecen' },
  { code: 'PRG', name: 'Prague' },
  { code: 'WAW', name: 'Warsaw' },
  { code: 'BER', name: 'Berlin' },
  { code: 'STN', name: 'London (STN)' },
  { code: 'LTN', name: 'London (LTN)' },
  { code: 'BGY', name: 'Milan (BGY)' },
  { code: 'FCO', name: 'Rome (FCO)' },
  { code: 'MAD', name: 'Madrid' },
  { code: 'BCN', name: 'Barcelona' },
];

export default function FilterChips({ params, onChange, onApply }) {
  const [activeDropdown, setActiveDropdown] = useState(null);

  const toggleDropdown = (name) => {
    setActiveDropdown(activeDropdown === name ? null : name);
  };

  const toggleOrigin = (code) => {
    let nextOrigins = Array.isArray(params.origins) ? [...params.origins] : [];
    if (nextOrigins.includes(code)) {
      if (nextOrigins.length > 1) {
        nextOrigins = nextOrigins.filter((c) => c !== code);
      }
    } else {
      nextOrigins.push(code);
    }
    onChange({ ...params, origins: nextOrigins });
  };

  const toggleWeekday = (dayId) => {
    let nextDays = [...params.departure_weekdays];
    if (nextDays.includes(dayId)) {
      if (nextDays.length > 1) {
        nextDays = nextDays.filter((d) => d !== dayId);
      }
    } else {
      nextDays.push(dayId);
    }
    nextDays.sort((a, b) => a - b);
    onChange({ ...params, departure_weekdays: nextDays });
  };

  const toggleAirline = (carrier) => {
    let nextAirlines = [...params.airlines];
    if (nextAirlines.includes(carrier)) {
      if (nextAirlines.length > 1) {
        nextAirlines = nextAirlines.filter((a) => a !== carrier);
      }
    } else {
      nextAirlines.push(carrier);
    }
    onChange({ ...params, airlines: nextAirlines });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm mb-6">
      <div className="flex flex-wrap items-center gap-2">
        {/* Origin Airports Chip - Editable & Dropdown */}
        <div className="relative">
          <div className="flex items-center bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
            <MapPin className="w-3.5 h-3.5 text-blue-600 mr-1.5 shrink-0" />
            <span className="text-xs text-gray-500 font-medium mr-1">From:</span>
            <input
              type="text"
              value={Array.isArray(params.origins) ? params.origins.join(', ') : params.origins}
              onChange={(e) => {
                const val = e.target.value;
                const codes = val.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean);
                onChange({ ...params, origins: codes.length ? codes : (val ? [val.toUpperCase()] : []) });
              }}
              placeholder="e.g. BUD, VIE, BER, STN..."
              title="Enter any origin airport code(s), e.g. BUD, BTS, VIE, STN, BER"
              className="text-xs font-semibold text-gray-900 bg-transparent focus:outline-none w-28 sm:w-44"
            />
            <button
              type="button"
              onClick={() => toggleDropdown('origins')}
              title="Quick select airports"
              className="ml-1 text-gray-400 hover:text-gray-700 cursor-pointer p-0.5"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          {activeDropdown === 'origins' && (
            <div className="absolute left-0 mt-2 w-72 max-w-[calc(100vw-3rem)] bg-white rounded-xl shadow-xl border border-gray-200 p-3 z-30">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">Quick Select Airports</p>
                <button
                  type="button"
                  onClick={() => onChange({ ...params, origins: ['BUD', 'DEB', 'BTS'] })}
                  className="text-[10px] text-blue-600 hover:underline font-semibold cursor-pointer"
                >
                  Reset Default
                </button>
              </div>
              <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                {POPULAR_AIRPORTS.map((apt) => {
                  const isSelected = Array.isArray(params.origins) && params.origins.includes(apt.code);
                  return (
                    <button
                      key={apt.code}
                      type="button"
                      onClick={() => toggleOrigin(apt.code)}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium cursor-pointer transition-colors ${
                        isSelected ? 'bg-blue-50 text-blue-800' : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <span className="flex items-center space-x-2">
                        <span className="font-bold">{apt.code}</span>
                        <span className="text-gray-500 font-normal">({apt.name})</span>
                      </span>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-600" />}
                    </button>
                  );
                })}
              </div>
              <p className="text-[10px] text-gray-400 mt-2 pt-2 border-t border-gray-100 italic">
                Tip: You can also type any custom airport code directly into the From field.
              </p>
            </div>
          )}
        </div>

        {/* Destination Chip */}
        <div className="relative">
          <div className="flex items-center bg-gray-50 border border-gray-200 rounded-xl px-3 py-1.5 focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
            <span className="text-xs text-gray-500 font-medium mr-1.5">To:</span>
            <input
              type="text"
              value={params.destination}
              onChange={(e) => onChange({ ...params, destination: e.target.value })}
              placeholder="Anywhere, London, Italy..."
              className="text-xs font-semibold text-gray-900 bg-transparent focus:outline-none w-28 sm:w-36"
            />
          </div>
        </div>

        {/* Nights Range Chip */}
        <div className="relative">
          <button
            type="button"
            onClick={() => toggleDropdown('nights')}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 text-gray-800 transition-all cursor-pointer"
          >
            <Moon className="w-3.5 h-3.5 text-indigo-600" />
            <span>{params.min_nights === params.max_nights ? `${params.min_nights} nights` : `${params.min_nights}–${params.max_nights} nights`}</span>
            <ChevronDown className="w-3 h-3 opacity-60" />
          </button>

          {activeDropdown === 'nights' && (
            <div className="absolute left-0 mt-2 w-64 max-w-[calc(100vw-3rem)] bg-white rounded-xl shadow-xl border border-gray-200 p-4 z-30">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Trip Length</p>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Min Nights:</span>
                  <div className="flex items-center space-x-2">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        onClick={() => onChange({ ...params, min_nights: n, max_nights: Math.max(n, params.max_nights) })}
                        className={`w-7 h-7 rounded-lg font-bold text-xs ${
                          params.min_nights === n ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Max Nights:</span>
                  <div className="flex items-center space-x-2">
                    {[2, 3, 4, 5, 7].map((n) => (
                      <button
                        key={n}
                        onClick={() => onChange({ ...params, max_nights: n, min_nights: Math.min(n, params.min_nights) })}
                        className={`w-7 h-7 rounded-lg font-bold text-xs ${
                          params.max_nights === n ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Departure Weekdays Chip */}
        <div className="relative">
          <button
            type="button"
            onClick={() => toggleDropdown('weekdays')}
            className="flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-xl border border-gray-200 bg-gray-50 hover:bg-gray-100 text-gray-800 transition-all cursor-pointer"
          >
            <CalendarIcon className="w-3.5 h-3.5 text-green-600" />
            <span>
              Out: {params.departure_weekdays.map((d) => WEEKDAYS[d]?.label).join(', ')}
            </span>
            <ChevronDown className="w-3 h-3 opacity-60" />
          </button>

          {activeDropdown === 'weekdays' && (
            <div className="absolute left-0 mt-2 w-64 max-w-[calc(100vw-3rem)] bg-white rounded-xl shadow-xl border border-gray-200 p-3 z-30">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Allowed Outbound Days</p>
              <div className="grid grid-cols-4 gap-1.5">
                {WEEKDAYS.map((w) => {
                  const isSelected = params.departure_weekdays.includes(w.id);
                  return (
                    <button
                      key={w.id}
                      onClick={() => toggleWeekday(w.id)}
                      className={`py-1.5 text-xs font-bold rounded-lg transition-colors ${
                        isSelected ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {w.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Open-Jaw Mode Toggle Chip */}
        <button
          type="button"
          onClick={() => onChange({ ...params, allow_open_jaw: !params.allow_open_jaw })}
          className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-xl border transition-all cursor-pointer ${
            params.allow_open_jaw
              ? 'bg-purple-50 border-purple-300 text-purple-800'
              : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
          }`}
          title="Open-Jaw allows departing from BUD and returning to BTS/DEB"
        >
          <RotateCw className="w-3.5 h-3.5 text-purple-600" />
          <span>{params.allow_open_jaw ? 'Open-Jaw (Any Home Airport)' : 'Same Airport Only'}</span>
        </button>

        {/* Include Ground Transfer Cost Toggle */}
        {params.allow_open_jaw && (
          <button
            type="button"
            onClick={() => onChange({ ...params, include_ground_transfer_cost: !params.include_ground_transfer_cost })}
            className={`flex items-center space-x-1.5 px-3 py-2 text-xs font-semibold rounded-xl border transition-all cursor-pointer ${
              params.include_ground_transfer_cost
                ? 'bg-amber-50 border-amber-300 text-amber-900'
                : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Bus className="w-3.5 h-3.5 text-amber-600" />
            <span>+ Ground Transit Cost ({params.include_ground_transfer_cost ? 'ON' : 'OFF'})</span>
          </button>
        )}

        {/* Apply / Refresh Button */}
        <div className="w-full sm:w-auto sm:ml-auto mt-1 sm:mt-0 flex justify-end">
          <button
            type="button"
            onClick={onApply}
            className="w-full sm:w-auto flex items-center justify-center space-x-1.5 px-4 py-2.5 sm:py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-all cursor-pointer"
          >
            <span>Update Results</span>
          </button>
        </div>
      </div>
    </div>
  );
}
