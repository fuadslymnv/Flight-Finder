import React from 'react';
import { MapPin, ArrowRight, Sparkles, AlertCircle } from 'lucide-react';

export default function ExploreView({ destinations, loading, onSelectDestination }) {
  if (loading) {
    return (
      <div className="py-16 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent mb-4"></div>
        <p className="text-sm font-medium text-gray-600">Discovering cheapest destinations across selected airports...</p>
      </div>
    );
  }

  if (!destinations || destinations.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-12 text-center">
        <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-3" />
        <h3 className="text-base font-bold text-gray-900 mb-1">No destinations found</h3>
        <p className="text-xs text-gray-500">Try broadening your travel window or night range.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900 tracking-tight">Explore Cheapest Destinations</h2>
          <p className="text-xs text-gray-500">Cheapest round trips found across selected origin airports</p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 bg-blue-50 text-blue-700 rounded-full border border-blue-200">
          {destinations.length} Destinations
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {destinations.map((dest) => {
          const currencySym = dest.currency === 'EUR' ? '€' : ' Ft';
          return (
            <div
              key={dest.destination_code}
              onClick={() => onSelectDestination(dest.destination_code)}
              className="bg-white rounded-2xl border border-gray-200 hover:border-blue-400 p-5 shadow-xs hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="text-base font-bold text-gray-900 group-hover:text-blue-600 transition-colors">
                      {dest.city_name}
                    </h3>
                    <p className="text-xs text-gray-500 font-medium">
                      {dest.country_name || dest.destination_code} ({dest.destination_code})
                    </p>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] font-bold rounded-md bg-gray-100 text-gray-700">
                    {dest.routes_available?.length || 1} routes
                  </span>
                </div>

                <p className="text-xs text-gray-500 mt-2">
                  Sample dates: <span className="font-semibold text-gray-700">{dest.example_dates}</span>
                </p>

                {dest.is_open_jaw_available && (
                  <div className="mt-2 inline-flex items-center text-[10px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded-full border border-purple-200">
                    Open-Jaw available
                  </div>
                )}
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between">
                <div>
                  <span className="text-[10px] text-gray-400 uppercase font-bold block">from</span>
                  <span className="text-xl font-black text-gray-900">
                    {Math.round(dest.cheapest_price).toLocaleString()}{currencySym}
                  </span>
                </div>

                <button
                  type="button"
                  className="flex items-center space-x-1 text-xs font-bold text-blue-600 group-hover:text-blue-700 group-hover:translate-x-0.5 transition-all"
                >
                  <span>View Flights</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
