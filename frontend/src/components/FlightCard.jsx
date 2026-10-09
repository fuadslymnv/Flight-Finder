import React, { useState } from 'react';
import { 
  PlaneTakeoff, 
  PlaneLanding, 
  ExternalLink, 
  Clock, 
  AlertTriangle, 
  ChevronDown, 
  ChevronUp, 
  Bus,
  ShieldCheck
} from 'lucide-react';

export default function FlightCard({ itinerary, index }) {
  const [expanded, setExpanded] = useState(false);
  const out = itinerary.outbound;
  const ret = itinerary.inbound;
  const currencySym = itinerary.currency === 'EUR' ? '€' : ' Ft';

  const formatTime = (isoStr) => {
    if (!isoStr) return '--:--';
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    return d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
  };

  const formatDuration = (sec) => {
    if (!sec) return '';
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    return `${h}h ${m}m`;
  };

  const isWizz = (code) => ['W6', 'W9'].includes(code?.toUpperCase());
  const isRyanair = (code) => ['FR', 'RK'].includes(code?.toUpperCase());

  return (
    <div className="bg-white rounded-2xl border border-gray-200 hover:border-blue-400 shadow-sm hover:shadow-md transition-all overflow-hidden mb-4">
      {/* Card Top Header */}
      <div className="px-5 py-3.5 bg-gray-50/80 border-b border-gray-100 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-800 text-xs font-bold flex items-center justify-center">
            {index}
          </span>
          <span className="text-base font-bold text-gray-900 tracking-tight">
            {itinerary.destination_city || out.destination}
          </span>
          <span className="text-xs px-2.5 py-0.5 rounded-full font-bold bg-gray-200 text-gray-700">
            {out.origin} ➔ {out.destination} ➔ {ret.destination}
          </span>
          <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-100">
            {itinerary.nights} {itinerary.nights === 1 ? 'night' : 'nights'}
          </span>
        </div>

        {/* Total Price & Booking */}
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <span className="text-2xl font-black text-gray-900">
              {Math.round(itinerary.total_price).toLocaleString()}{currencySym}
            </span>
            <div className="text-[11px] text-gray-500 font-medium">
              total base fare {itinerary.ground_transfer_cost > 0 && `(incl. transit)`}
            </div>
          </div>
        </div>
      </div>

      {/* Open-Jaw Banner (if applicable) */}
      {itinerary.is_open_jaw && (
        <div className="px-5 py-2.5 bg-amber-50/90 border-b border-amber-200/60 flex items-start space-x-2 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold mr-1">OPEN-JAW TRIP:</span>
            <span>
              Depart from <strong className="font-semibold">{out.origin}</strong>, return to <strong className="font-semibold">{ret.destination}</strong>.
            </span>
            {itinerary.ground_transfer && (
              <div className="mt-1 flex items-center space-x-1.5 text-amber-800 font-medium">
                <Bus className="w-3.5 h-3.5 text-amber-600" />
                <span>
                  Ground transit ({itinerary.ground_transfer.return_airport} ➔ {itinerary.ground_transfer.origin_airport}): ~{itinerary.ground_transfer.transit_hours}h 
                  ({itinerary.currency === 'EUR' ? `~${itinerary.ground_transfer.estimated_cost_eur}€` : `~${itinerary.ground_transfer.estimated_cost_huf} Ft`}) — {itinerary.ground_transfer.transit_description}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Outbound & Inbound Legs */}
      <div className="p-5 space-y-4">
        {/* Outbound Leg */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-100">
          <div className="flex items-center space-x-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
              isWizz(out.carrier_code) 
                ? 'bg-[#c6007e] text-white' 
                : 'bg-[#0d2c6c] text-[#f1c40f]'
            }`}>
              {out.carrier_code}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Outbound</span>
                <span className="text-xs font-medium text-gray-400">•</span>
                <span className="text-xs font-semibold text-gray-700">{formatDate(out.departure_time)}</span>
              </div>
              <div className="text-sm font-bold text-gray-900 mt-0.5">
                {formatTime(out.departure_time)} <span className="text-gray-400 font-normal">{out.origin}</span> ➔ {formatTime(out.arrival_time)} <span className="text-gray-400 font-normal">{out.destination}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between sm:justify-end space-x-4">
            <div className="text-xs text-gray-500 text-left sm:text-right">
              <div className="flex items-center space-x-1 sm:justify-end">
                <Clock className="w-3 h-3 text-gray-400" />
                <span>{formatDuration(out.duration_seconds)} (Direct)</span>
              </div>
              <span className="font-semibold text-gray-700">{out.carrier_name} {out.flight_number}</span>
            </div>
            <div className="text-right">
              <span className="text-sm font-bold text-gray-900">
                {Math.round(out.price).toLocaleString()}{currencySym}
              </span>
              <div className="text-[10px] text-gray-400">per leg</div>
            </div>
          </div>
        </div>

        {/* Return Leg */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
              isWizz(ret.carrier_code) 
                ? 'bg-[#c6007e] text-white' 
                : 'bg-[#0d2c6c] text-[#f1c40f]'
            }`}>
              {ret.carrier_code}
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Return</span>
                <span className="text-xs font-medium text-gray-400">•</span>
                <span className="text-xs font-semibold text-gray-700">{formatDate(ret.departure_time)}</span>
              </div>
              <div className="text-sm font-bold text-gray-900 mt-0.5">
                {formatTime(ret.departure_time)} <span className="text-gray-400 font-normal">{ret.origin}</span> ➔ {formatTime(ret.arrival_time)} <span className="text-gray-400 font-normal">{ret.destination}</span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between sm:justify-end space-x-4">
            <div className="text-xs text-gray-500 text-left sm:text-right">
              <div className="flex items-center space-x-1 sm:justify-end">
                <Clock className="w-3 h-3 text-gray-400" />
                <span>{formatDuration(ret.duration_seconds)} (Direct)</span>
              </div>
              <span className="font-semibold text-gray-700">{ret.carrier_name} {ret.flight_number}</span>
            </div>
            <div className="text-right">
              <span className="text-sm font-bold text-gray-900">
                {Math.round(ret.price).toLocaleString()}{currencySym}
              </span>
              <div className="text-[10px] text-gray-400">per leg</div>
            </div>
          </div>
        </div>
      </div>

      {/* Action Booking Bar */}
      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-semibold text-gray-600 hover:text-gray-900 flex items-center space-x-1 cursor-pointer"
        >
          <span>{expanded ? 'Hide Details' : 'Flight Details'}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {/* Dual Booking Buttons */}
        <div className="flex items-center space-x-2">
          {/* Direct Airline Booking Links */}
          {(out.direct_airline_url || ret.direct_airline_url) && (
            <div className="flex items-center space-x-1">
              {out.direct_airline_url && (
                <a
                  href={out.direct_airline_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 text-xs font-semibold text-gray-700 bg-white hover:bg-gray-100 border border-gray-300 rounded-lg flex items-center space-x-1 transition-all"
                  title="Book Outbound leg directly on airline site"
                >
                  <span>Book Outbound ({out.carrier_code})</span>
                  <ExternalLink className="w-3 h-3 text-gray-400" />
                </a>
              )}
              {ret.direct_airline_url && (
                <a
                  href={ret.direct_airline_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1 text-xs font-semibold text-gray-700 bg-white hover:bg-gray-100 border border-gray-300 rounded-lg flex items-center space-x-1 transition-all"
                  title="Book Return leg directly on airline site"
                >
                  <span>Book Return ({ret.carrier_code})</span>
                  <ExternalLink className="w-3 h-3 text-gray-400" />
                </a>
              )}
            </div>
          )}

          {/* Kiwi Deep Link Button */}
          {(out.booking_url || ret.booking_url) && (
            <a
              href={out.booking_url || ret.booking_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3.5 py-1.5 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg flex items-center space-x-1.5 shadow-xs transition-all"
            >
              <span>Book on Kiwi</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>

      {/* Expanded Details Section */}
      {expanded && (
        <div className="px-5 py-4 bg-gray-50/50 border-t border-gray-200 text-xs text-gray-600 space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white p-3 rounded-xl border border-gray-200">
              <p className="font-bold text-gray-900 mb-1">Outbound Flight Details</p>
              <p>Flight: <span className="font-semibold">{out.carrier_name} {out.flight_number}</span></p>
              <p>Departs: <span className="font-semibold">{out.origin_city || out.origin} ({out.origin})</span> at {formatTime(out.departure_time)}</p>
              <p>Arrives: <span className="font-semibold">{out.destination_city || out.destination} ({out.destination})</span> at {formatTime(out.arrival_time)}</p>
              <p>Date: <span className="font-semibold">{out.departure_date}</span></p>
            </div>
            <div className="bg-white p-3 rounded-xl border border-gray-200">
              <p className="font-bold text-gray-900 mb-1">Return Flight Details</p>
              <p>Flight: <span className="font-semibold">{ret.carrier_name} {ret.flight_number}</span></p>
              <p>Departs: <span className="font-semibold">{ret.origin_city || ret.origin} ({ret.origin})</span> at {formatTime(ret.departure_time)}</p>
              <p>Arrives: <span className="font-semibold">{ret.destination_city || ret.destination} ({ret.destination})</span> at {formatTime(ret.arrival_time)}</p>
              <p>Date: <span className="font-semibold">{ret.departure_date}</span></p>
            </div>
          </div>
          <p className="text-gray-400 italic">
            * Note: Both airlines price one-way legs independently. Luggage and seat selection extra.
          </p>
        </div>
      )}
    </div>
  );
}
