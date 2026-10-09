const API_BASE = '/api';

export async function parseQuery(query) {
  const res = await fetch(`${API_BASE}/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function searchFlights(params, forceRefresh = false) {
  const url = `${API_BASE}/search${forceRefresh ? '?force_refresh=true' : ''}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function exploreDestinations(params) {
  const res = await fetch(`${API_BASE}/explore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getCalendarHeatmap(req) {
  const res = await fetch(`${API_BASE}/calendar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getSettings() {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function updateSettings(settings) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function clearCache() {
  const res = await fetch(`${API_BASE}/cache/clear`, { method: 'POST' });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
