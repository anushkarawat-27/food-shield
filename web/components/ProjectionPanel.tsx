"use client";

import { useEffect, useState } from "react";
import { useStore } from "@/lib/store";
import { project } from "@/lib/api";

type Row = {
  region_id: number;
  horizon_months: number;
  ipc_phase: number;
  ci_low: number;
  ci_high: number;
};

const PHASE_COLOR = (p: number) =>
  p < 2 ? "#22c55e" : p < 3 ? "#eab308" : p < 4 ? "#f97316" : "#ef4444";

export default function ProjectionPanel() {
  const regionId = useStore((s) => s.selectedRegionId);
  const scenario = useStore((s) => s.scenario);
  const [rows, setRows] = useState<Row[]>([]);

  useEffect(() => {
    if (regionId == null || !scenario[regionId]) {
      setRows([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r: Row[] = await project({ [regionId]: scenario[regionId] });
        setRows(r);
      } catch {
        setRows([]);
      }
    }, 300);
    return () => clearTimeout(t);
  }, [regionId, scenario]);

  if (regionId == null) return null;
  if (rows.length === 0) {
    return (
      <div className="border-t border-white/10 pt-4">
        <div className="text-xs uppercase opacity-50 mb-1">Projection</div>
        <div className="text-xs opacity-50">Adjust a slider to project IPC phases.</div>
      </div>
    );
  }

  return (
    <div className="border-t border-white/10 pt-4">
      <div className="text-xs uppercase opacity-50 mb-2">Projected IPC phase</div>
      <ul className="space-y-2">
        {rows.map((r) => {
          const pct = (r.ipc_phase / 5) * 100;
          const ciLowPct = (r.ci_low / 5) * 100;
          const ciHighPct = (r.ci_high / 5) * 100;
          return (
            <li key={r.horizon_months} className="text-sm">
              <div className="flex justify-between">
                <span>{r.horizon_months}-month</span>
                <span className="opacity-80">
                  phase {r.ipc_phase.toFixed(1)}{" "}
                  <span className="opacity-50">
                    ({r.ci_low.toFixed(1)}–{r.ci_high.toFixed(1)})
                  </span>
                </span>
              </div>
              <div className="relative h-2 mt-1 rounded bg-white/5 overflow-hidden">
                <div
                  className="absolute inset-y-0 bg-white/15"
                  style={{ left: `${ciLowPct}%`, width: `${ciHighPct - ciLowPct}%` }}
                />
                <div
                  className="absolute inset-y-0"
                  style={{
                    left: `${Math.max(0, pct - 1)}%`,
                    width: "2%",
                    backgroundColor: PHASE_COLOR(r.ipc_phase),
                  }}
                />
              </div>
            </li>
          );
        })}
      </ul>
      <div className="text-[10px] opacity-50 mt-2">
        1=Minimal · 2=Stressed · 3=Crisis · 4=Emergency · 5=Famine
      </div>
    </div>
  );
}
