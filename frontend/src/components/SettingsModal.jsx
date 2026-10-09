import React, { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api';
import { X, Save, Bus, Shield, RotateCcw, Check } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose }) {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isOpen) {
      load();
    }
  }, [isOpen]);

  const load = async () => {
    try {
      const data = await getSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    setLoading(true);
    try {
      await updateSettings(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error('Failed to save settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const updatePreset = (routeKey, field, val) => {
    setSettings((prev) => ({
      ...prev,
      ground_transfers: {
        ...prev.ground_transfers,
        [routeKey]: {
          ...prev.ground_transfers[routeKey],
          [field]: val,
        },
      },
    }));
  };

  if (!isOpen || !settings) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs">
      <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-gray-200">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-lg font-bold text-gray-900 tracking-tight">Settings & Presets</h2>
            <p className="text-xs text-gray-500">Configure ground-transfer estimates and app defaults</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-full transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Ground Transfer Presets */}
          <div>
            <div className="flex items-center space-x-2 mb-3">
              <Bus className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold text-gray-900">Ground Transfer Presets (Open-Jaw)</h3>
            </div>
            <p className="text-xs text-gray-500 mb-4">
              Estimated travel times and ground transport costs between your home airports when flying out of one and returning to another.
            </p>

            <div className="space-y-4">
              {Object.entries(settings.ground_transfers || {}).map(([key, preset]) => (
                <div key={key} className="p-4 rounded-2xl bg-gray-50 border border-gray-200 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-blue-800 bg-blue-100 px-2.5 py-1 rounded-lg">
                      {preset.route} ({preset.from_airport} ➔ {preset.to_airport})
                    </span>
                    <span className="text-xs text-gray-500 font-medium">{preset.description}</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-gray-600 mb-1">Transit Time (hours)</label>
                      <input
                        type="number"
                        step="0.5"
                        value={preset.transit_hours}
                        onChange={(e) => updatePreset(key, 'transit_hours', parseFloat(e.target.value) || 0)}
                        className="w-full px-3 py-1.5 text-xs font-semibold rounded-xl border border-gray-300 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-gray-600 mb-1">Cost in EUR (€)</label>
                      <input
                        type="number"
                        value={preset.cost_eur}
                        onChange={(e) => updatePreset(key, 'cost_eur', parseFloat(e.target.value) || 0)}
                        className="w-full px-3 py-1.5 text-xs font-semibold rounded-xl border border-gray-300 bg-white"
                      />
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-gray-600 mb-1">Cost in HUF (Ft)</label>
                      <input
                        type="number"
                        value={preset.cost_huf}
                        onChange={(e) => updatePreset(key, 'cost_huf', parseFloat(e.target.value) || 0)}
                        className="w-full px-3 py-1.5 text-xs font-semibold rounded-xl border border-gray-300 bg-white"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cache Settings */}
          <div className="pt-4 border-t border-gray-100">
            <div className="flex items-center space-x-2 mb-3">
              <Shield className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-bold text-gray-900">Cache & Performance</h3>
            </div>
            <div className="flex items-center justify-between p-4 rounded-2xl bg-gray-50 border border-gray-200">
              <div>
                <p className="text-xs font-bold text-gray-800">Flight Leg Cache TTL</p>
                <p className="text-[11px] text-gray-500">Duration to keep one-way leg prices cached in SQLite</p>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  min="1"
                  max="24"
                  value={settings.cache_ttl_hours}
                  onChange={(e) => setSettings({ ...settings, cache_ttl_hours: parseInt(e.target.value) || 4 })}
                  className="w-16 px-2 py-1 text-xs font-bold rounded-lg border border-gray-300 bg-white text-center"
                />
                <span className="text-xs text-gray-500 font-medium">hours</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between sticky bottom-0 rounded-b-3xl">
          <span className="text-xs text-gray-400">
            {saved ? <span className="text-emerald-600 font-bold flex items-center gap-1"><Check className="w-3.5 h-3.5" /> Saved!</span> : 'Changes are saved locally'}
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200 rounded-xl transition-colors cursor-pointer"
            >
              Close
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-xs flex items-center space-x-1.5 transition-all cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{loading ? 'Saving...' : 'Save Settings'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
