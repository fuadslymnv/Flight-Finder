import React from 'react';
import { Plane, Settings, RotateCcw, Sparkles } from 'lucide-react';

export default function Header({ currency, setCurrency, onOpenSettings, onClearCache }) {
  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Plane className="w-5 h-5 -rotate-45" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xl font-bold tracking-tight text-gray-900">FlightFinder</span>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                BUD • DEB • BTS
              </span>
            </div>
            <p className="text-xs text-gray-500 font-medium hidden sm:block">
              Wizz Air & Ryanair • Open-Jaw Smart Combos
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Currency Toggle */}
          <div className="flex items-center bg-gray-100 p-0.5 rounded-lg border border-gray-200">
            <button
              onClick={() => setCurrency('EUR')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
                currency === 'EUR'
                  ? 'bg-white text-blue-700 shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              EUR €
            </button>
            <button
              onClick={() => setCurrency('HUF')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all ${
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
            className="p-2 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            title="Settings & Ground Transfer Presets"
            className="flex items-center space-x-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded-lg transition-colors"
          >
            <Settings className="w-4 h-4 text-gray-500" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </div>
    </header>
  );
}
