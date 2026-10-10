import React, { useState, useEffect } from 'react';
import { getCalendarHeatmap } from '../api';
import { Calendar as CalendarIcon, Loader2, Sparkles } from 'lucide-react';

export default function CalendarHeatmap({ destination, params, currency, onSelectDate }) {
  const [heatmapData, setHeatmapData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [destInput, setDestInput] = useState(destination && destination !== 'anywhere' ? destination : 'London');

  const fetchHeatmap = async (targetDest) => {
    if (!targetDest || targetDest === 'anywhere') return;
    setLoading(true);
    try {
      const data = await getCalendarHeatmap({
        destination: targetDest,
        date_from: params.date_from,
        date_to: params.date_to,
        min_nights: 2,
        max_nights: 4,
        origins: params.origins,
        currency: currency,
        allow_open_jaw: params.allow_open_jaw,
      });
      setHeatmapData(data);
    } catch (err) {
      console.error('Failed to load heatmap:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (destination && destination !== 'anywhere') {
      setDestInput(destination);
      fetchHeatmap(destination);
    } else {
      fetchHeatmap(destInput);
    }
  }, [destination, currency, params.date_from, params.date_to]);

  const currencySym = currency === 'EUR' ? '€' : ' Ft';

  // Group cells by departure date
  const dateMap = {};
  const allPrices = [];

  heatmapData.forEach((cell) => {
    if (!dateMap[cell.departure_date]) {
      dateMap[cell.departure_date] = {};
    }
    dateMap[cell.departure_date][cell.nights] = cell;
    if (cell.cheapest_price != null) {
      allPrices.push(cell.cheapest_price);
    }
  });

  const minPrice = allPrices.length ? Math.min(...allPrices) : 0;
  const maxPrice = allPrices.length ? Math.max(...allPrices) : 100;

  const getHeatmapColor = (price) => {
    if (price == null) return 'bg-gray-100 text-gray-400';
    const range = maxPrice - minPrice || 1;
    const ratio = (price - minPrice) / range;
    if (ratio < 0.25) return 'bg-emerald-100 text-emerald-900 font-bold border-emerald-300';
    if (ratio < 0.6) return 'bg-yellow-100 text-yellow-900 font-semibold border-yellow-300';
    return 'bg-rose-50 text-rose-900 border-rose-200';
  };

  const dates = Object.keys(dateMap).sort();

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-gray-100">
        <div>
          <h2 className="text-lg font-bold text-gray-900 tracking-tight flex items-center gap-2">
            <CalendarIcon className="w-5 h-5 text-blue-600" />
            <span>Price Heatmap Matrix</span>
          </h2>
          <p className="text-xs text-gray-500">Departure date × Trip length matrix for lowest total fares</p>
        </div>

        {/* Destination Picker */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-gray-600">Destination:</span>
          <input
            type="text"
            value={destInput}
            onChange={(e) => setDestInput(e.target.value)}
            className="text-xs font-bold px-3 py-1.5 rounded-xl border border-gray-300 focus:outline-none focus:border-blue-500 w-28 sm:w-32"
          />
          <button
            onClick={() => fetchHeatmap(destInput)}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-all cursor-pointer"
          >
            {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Update Grid'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-16 text-center">
          <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
          <p className="text-xs text-gray-500">Calculating cheapest price matrix...</p>
        </div>
      ) : dates.length === 0 ? (
        <div className="py-12 text-center text-xs text-gray-500">
          No flight data available for this destination in the selected travel window.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 text-gray-500">
                <th className="py-2.5 px-3 font-semibold">Departure Date</th>
                <th className="py-2.5 px-3 font-semibold text-center">2 Nights</th>
                <th className="py-2.5 px-3 font-semibold text-center">3 Nights</th>
                <th className="py-2.5 px-3 font-semibold text-center">4 Nights</th>
              </tr>
            </thead>
            <tbody>
              {dates.map((dStr) => {
                const d = new Date(dStr);
                const dayName = d.toLocaleDateString([], { weekday: 'short' });
                const dateFmt = d.toLocaleDateString([], { day: 'numeric', month: 'short' });
                const isWeekend = [5, 6].includes(d.getDay()); // Sat, Sun

                return (
                  <tr key={dStr} className="border-b border-gray-100 hover:bg-gray-50/80 transition-colors">
                    <td className="py-2 px-3 font-medium text-gray-800">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[11px] mr-1.5 font-semibold ${
                        isWeekend ? 'bg-indigo-100 text-indigo-800' : 'text-gray-500'
                      }`}>
                        {dayName}
                      </span>
                      <span>{dateFmt}</span>
                    </td>

                    {[2, 3, 4].map((n) => {
                      const cell = dateMap[dStr]?.[n];
                      const price = cell?.cheapest_price;
                      return (
                        <td key={n} className="py-2 px-3 text-center">
                          {price != null ? (
                            <div
                              onClick={() => onSelectDate && onSelectDate(dStr, n)}
                              className={`inline-block px-3 py-1 rounded-xl border text-xs cursor-pointer shadow-2xs transition-all hover:scale-105 ${getHeatmapColor(
                                price
                              )}`}
                              title={`Cheapest ${n}-night trip: ${Math.round(price)}${currencySym} (${cell.carrier_summary})`}
                            >
                              <span>{Math.round(price)}{currencySym}</span>
                            </div>
                          ) : (
                            <span className="text-gray-300">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
