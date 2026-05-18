const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getRegions(adminLevel = 0) {
  const r = await fetch(`${BASE}/regions?admin_level=${adminLevel}`);
  if (!r.ok) throw new Error("regions fetch failed");
  return r.json();
}

export async function getRegionsGeoJSON(adminLevel = 0) {
  const r = await fetch(`${BASE}/regions/geojson?admin_level=${adminLevel}`);
  if (!r.ok) throw new Error("geojson fetch failed");
  return r.json();
}

export async function getEventsGeoJSON(days = 30) {
  const r = await fetch(`${BASE}/events/geojson?days=${days}`);
  if (!r.ok) throw new Error("events geojson failed");
  return r.json();
}

export async function getEventsSummary(days = 30) {
  const r = await fetch(`${BASE}/events/summary?days=${days}`);
  if (!r.ok) throw new Error("events summary failed");
  return r.json();
}

export type RegionInputs = {
  drought: number; flood: number; heat: number; pest: number; frost: number;
};
export type Scenario = Record<number, RegionInputs>;

export async function simulate(scenario: Scenario) {
  const r = await fetch(`${BASE}/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario }),
  });
  if (!r.ok) throw new Error("simulate failed");
  return r.json();
}

export async function project(scenario: Scenario, horizons = [3, 6, 12]) {
  const r = await fetch(`${BASE}/project`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, horizons_months: horizons }),
  });
  if (!r.ok) throw new Error("project failed");
  return r.json();
}

export async function recommend(
  scenario: Scenario,
  totalTonnage: number,
  totalBudgetUsd: number,
  priorityGroups: string[] = [],
  avoidConflictZones = true,
) {
  const r = await fetch(`${BASE}/recommend`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      scenario,
      total_tonnage: totalTonnage,
      total_budget_usd: totalBudgetUsd,
      priority_population_groups: priorityGroups,
      avoid_conflict_zones: avoidConflictZones,
    }),
  });
  if (!r.ok) throw new Error("recommend failed");
  return r.json();
}
