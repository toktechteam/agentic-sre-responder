// ui/src/api.js

// Same-origin API calls (NGINX proxies to backend)
const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

function buildUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

async function handleResponse(res, url) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} for ${url}: ${text}`);
  }
  return res.json();
}

export async function fetchIncidents() {
  const url = buildUrl("/incidents");
  const res = await fetch(url);
  return handleResponse(res, url);
}

export async function fetchIncident(incidentId) {
  const url = buildUrl(`/incidents/${incidentId}`);
  const res = await fetch(url);
  return handleResponse(res, url);
}

export async function injectDemo(payload) {
  const url = buildUrl("/demo/inject");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, url);
}

export async function fetchDemoWorkloads() {
  const url = buildUrl("/demo/workloads");
  const res = await fetch(url);
  return handleResponse(res, url);
}

export async function triggerDemoAttack(payload) {
  const url = buildUrl("/demo/attack");
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handleResponse(res, url);
}
