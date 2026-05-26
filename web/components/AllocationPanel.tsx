"use client";

import { useState } from "react";
import { useStore } from "@/lib/store";
import { recommend } from "@/lib/api";

type Allocation = {
  region_id: number;
  tonnes: number;
  from_depot: string;
  cost_usd: number;
  coverage_pct: number;
};

type Result = {
  allocations: Allocation[];
  unmet_demand_tonnes: number;
  total_cost_usd: number;
};

export default function AllocationPanel() {
  const scenario = useStore((s) => s.scenario);
  const [tonnage, setTonnage] = useState(50000);
  const [budget, setBudget] = useState(20_000_000);
  const [avoidConflict, setAvoidConflict] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Result | null>(null);

  const hasScenario = Object.keys(scenario).length > 0;

  async function run() {
    if (!hasScenario) return;
    setLoading(true);
    try {
      const r = await recommend(scenario, tonnage, budget, [], avoidConflict);
      setResult(r);
    } catch (e) {
      console.error(e);
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border-t border-white/10 pt-4 space-y-3">
      <div className="text-xs uppercase opacity-50">Allocation recommender</div>

      <label className="block text-sm">
        <div className="flex justify-between">
          <span>Tonnage available</span>
          <span className="opacity-70">{tonnage.toLocaleString()} t</span>
        </div>
        <input
          type="range"
          min={1000}
          max={500000}
          step={1000}
          value={tonnage}
          onChange={(e) => setTonnage(parseInt(e.target.value))}
          className="w-full accent-emerald-400"
        />
      </label>

      <label className="block text-sm">
        <div className="flex justify-between">
          <span>Budget (USD)</span>
          <span className="opacity-70">${(budget / 1_000_000).toFixed(1)}M</span>
        </div>
        <input
          type="range"
          min={1_000_000}
          max={500_000_000}
          step={1_000_000}
          value={budget}
          onChange={(e) => setBudget(parseInt(e.target.value))}
          className="w-full accent-emerald-400"
        />
      </label>

      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={avoidConflict}
          onChange={(e) => setAvoidConflict(e.target.checked)}
          className="accent-emerald-400"
        />
        Avoid conflict zones
      </label>

      <button
        onClick={run}
        disabled={!hasScenario || loading}
        className="w-full bg-emerald-500/90 hover:bg-emerald-500 disabled:bg-white/10 disabled:text-white/40 text-black text-sm font-medium rounded px-3 py-2"
      >
        {loading ? "Optimizing..." : "Run allocation"}
      </button>

      <button
        onClick={async () => {
          if (!hasScenario) return;
          const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          const res = await fetch(`${apiBase}/export/policy`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              scenario,
              total_tonnage: tonnage,
              total_budget_usd: budget,
              priority_population_groups: [],
              avoid_conflict_zones: avoidConflict,
              filename: `foodshield_policy_${new Date().toISOString().slice(0, 10)}.csv`,
            }),
          });
          if (!res.ok) return;
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `foodshield_policy_${new Date().toISOString().slice(0, 10)}.csv`;
          a.click();
          URL.revokeObjectURL(url);
        }}
        disabled={!hasScenario || !result}
        className="w-full border border-white/20 hover:bg-white/10 disabled:opacity-40 text-xs rounded px-3 py-2"
      >
        Export policy CSV
      </button>

      {!hasScenario && (
        <div className="text-xs opacity-50">
          Move disruptor sliders on at least one region first.
        </div>
      )}

      {result && (
        <div className="text-sm space-y-2 pt-2">
          <div className="flex justify-between">
            <span className="opacity-70">Delivered</span>
            <span>
              {result.allocations.reduce((s, a) => s + a.tonnes, 0).toLocaleString()} t
            </span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-70">Unmet demand</span>
            <span>{result.unmet_demand_tonnes.toLocaleString()} t</span>
          </div>
          <div className="flex justify-between">
            <span className="opacity-70">Total cost</span>
            <span>${(result.total_cost_usd / 1_000_000).toFixed(2)}M</span>
          </div>

          {result.allocations.length > 0 && (
            <div className="max-h-48 overflow-y-auto border border-white/10 rounded">
              <table className="w-full text-xs">
                <thead className="bg-white/5">
                  <tr>
                    <th className="text-left px-2 py-1">Region</th>
                    <th className="text-right px-2 py-1">Tonnes</th>
                    <th className="text-right px-2 py-1">Cover</th>
                  </tr>
                </thead>
                <tbody>
                  {result.allocations.map((a) => (
                    <tr key={`${a.region_id}-${a.from_depot}`} className="border-t border-white/5">
                      <td className="px-2 py-1">#{a.region_id}</td>
                      <td className="text-right px-2 py-1">{a.tonnes.toLocaleString()}</td>
                      <td className="text-right px-2 py-1">{a.coverage_pct.toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
