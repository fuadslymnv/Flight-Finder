import React, { useState } from 'react';
import { Search, Sparkles, ArrowRight, Loader2 } from 'lucide-react';

const SUGGESTIONS = [
  "cheap 2-3 night trip, leave Fri or Sat, next 2 months",
  "weekend in London in Nov",
  "Milan or Rome under 50 EUR",
  "leave from BTS to anywhere for 3-4 nights",
  "Budapest to Poland weekend trip",
];

export default function SearchBar({ onParseAndSearch, loading }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    onParseAndSearch(query);
  };

  const handleSuggestionClick = (sug) => {
    setQuery(sug);
    onParseAndSearch(sug);
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="relative flex items-center shadow-lg rounded-2xl overflow-hidden border border-gray-200 bg-white focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent transition-all">
        <div className="pl-4 sm:pl-5 text-blue-600">
          <Search className="w-5 h-5 sm:w-6 sm:h-6" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="E.g. cheap 2-3 night trip, leave Fri or Sat, next 2 months..."
          className="w-full py-4 sm:py-4.5 px-3 sm:px-4 text-sm sm:text-base text-gray-900 placeholder-gray-400 bg-transparent focus:outline-none"
        />
        <div className="pr-2 sm:pr-3">
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center space-x-1.5 px-4 sm:px-5 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium text-sm rounded-xl transition-all shadow-sm shadow-blue-500/20 cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="hidden sm:inline">Searching...</span>
              </>
            ) : (
              <>
                <span>Search</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Suggestion Chips */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5 sm:gap-2">
        <span className="text-xs font-semibold text-gray-500 flex items-center gap-1 mr-1">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Ideas:
        </span>
        {SUGGESTIONS.map((sug, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSuggestionClick(sug)}
            className="text-xs bg-white hover:bg-blue-50 text-gray-700 hover:text-blue-700 px-3 py-1 rounded-full border border-gray-200 hover:border-blue-300 transition-all cursor-pointer shadow-2xs"
          >
            {sug}
          </button>
        ))}
      </div>
    </div>
  );
}
