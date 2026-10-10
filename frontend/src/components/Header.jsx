import React from 'react';
import { Plane, Settings, RotateCcw, Sparkles } from 'lucide-react';

export default function Header({ currency, setCurrency, onOpenSettings, onClearCache }) {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-2">
        {/* Brand */}
        <div className="flex items-center space-x-2 sm:space-x-3 min-w-0">
          <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 shrink-0">
            <Plane className="w-4 h-4 sm:w-5 sm:h-5 -rotate-45" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-1.5 sm:space-x-2">
              <span className="text-base sm:text-xl font-bold tracking-tight text-gray-900 truncate">FlightFinder</span>
              <span className="hidden xs:inline-block px-1.5 sm:px-2 py-0.5 text-[10px] sm:text-xs font-semibold rounded-full bg-blue-100 text-blue-800 shrink-0">
                All Airports
              </span>
            </div>
            <p className="text-[11px] sm:text-xs text-gray-500 font-medium hidden md:block">
              Wizz Air & Ryanair • Open-Jaw Smart Combos from Any Airport
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-1.5 sm:space-x-2.5 shrink-0">
          {/* Currency Toggle */}
          <div className="flex items-center bg-gray-100 p-0.5 rounded-lg border border-gray-200">
            <button
              onClick={() => setCurrency('EUR')}
              className={`px-2 sm:px-3 py-1 sm:py-1.5 text-[11px] sm:text-xs font-semibold rounded-md transition-all cursor-pointer ${
                currency === 'EUR'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              EUR €
            </button>
            <button
              onClick={() => setCurrency('HUF')}
              className={`px-2 sm:px-3 py-1 sm:py-1.5 text-[11px] sm:text-xs font-semibold rounded-md transition-all cursor-pointer ${
                currency === 'HUF'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              HUF Ft
            </button>
          </div>

          {/* Clear Cache Button */}
          <button
            onClick={onClearCache}
            title="Clear cached flight data"
            className="p-1.5 sm:p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            title="Settings & Ground Transfer Presets"
            className="flex items-center space-x-1 px-2.5 sm:px-3 py-1 sm:py-1.5 text-[11px] sm:text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded-lg transition-colors cursor-pointer"
          >
            <Settings className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-gray-500" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </div>
    </header>
  );
}
