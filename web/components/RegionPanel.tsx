"use client";

import { useStore, DEFAULT_INPUTS } from "@/lib/store";
import type { RegionInputs } from "@/lib/api";
import ProjectionPanel from "./ProjectionPanel";
import AllocationPanel from "./AllocationPanel";

const DISRUPTORS: { key: keyof RegionInputs; label: string }[] = [
  { key: "drought", label: "Drought" },
  { key: "flood", label: "Flooding" },
  { key: "heat", label: "Extreme heat" },
  { key: "pest", label: "Pest swarm" },
  { key: "frost", label: "Frost" },
];

export default function RegionPanel() {
  const regionId = useStore((s) => s.selectedRegionId);
  const inputs = useStore((s) =>
    regionId != null ? s.scenario[regionId] ?? DEFAULT_INPUTS : DEFAULT_INPUTS,
  );
  const impact = useStore((s) => (regionId != null ? s.impacts[regionId] : undefined));
  const setInput = useStore((s) => s.setInput);
  const reset = useStore((s) => s.reset);

  if (regionId == null) {
    return (
      <div className="p-6 text-sm opacity-60">
        Click a region on the map to load its disruptor controls.
      </div>
    );
  }

  return (
    <div className="p-5 space-y-5">
      <div>
        <div className="text-xs uppercase opacity-50">Region #{regionId}</div>
        <h2 className="text-lg font-semibold">Disruptor controls</h2>
      </div>

      {DISRUPTORS.map(({ key, label }) => (
        <label key={key} className="block">
          <div className="flex justify-between text-sm">
            <span>{label}</span>
            <span className="opacity-70">{(inputs[key] * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={inputs[key]}
            onChange={(e) => setInput(regionId, key, parseFloat(e.target.value))}
            className="w-full accent-emerald-400"
          />
        </label>
      ))}

      <div className="border-t border-white/10 pt-4 text-sm">
        <div className="opacity-70 mb-1">Projected impact</div>
        {impact ? (
          <ul className="space-y-1">
            <li>
              Yield Δ:{" "}
              <span className="text-emerald-300">{impact.yield_delta_pct}%</span>
            </li>
            <li>
              Affected pop:{" "}
              {impact.affected_population.toLocaleString()}
            </li>
          </ul>
        ) : (
          <div className="opacity-50">Move a slider to simulate.</div>
        )}
      </div>

      <ProjectionPanel />
      <AllocationPanel />

      <button
        onClick={reset}
        className="text-xs underline opacity-70 hover:opacity-100"
      >
        Reset scenario
      </button>
    </div>
  );
}
