"use client";

import { useEffect } from "react";
import WorldMap from "./WorldMap";
import RegionPanel from "./RegionPanel";
import Legend from "./Legend";
import { useStore } from "@/lib/store";
import { simulate } from "@/lib/api";

export default function Dashboard() {
  const scenario = useStore((s) => s.scenario);
  const setImpacts = useStore((s) => s.setImpacts);

  useEffect(() => {
    if (Object.keys(scenario).length === 0) {
      setImpacts([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const rows = await simulate(scenario);
        setImpacts(rows);
      } catch (e) {
        console.error(e);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [scenario, setImpacts]);

  return (
    <div className="flex h-screen w-screen">
      <main className="flex-1 relative">
        <header className="absolute top-0 left-0 z-10 p-4">
          <h1 className="text-xl font-semibold tracking-tight">
            <span className="text-emerald-400">Food</span>Shield
          </h1>
          <p className="text-xs opacity-60">
            Disruptor simulator · projection · aid allocation
          </p>
        </header>
        <WorldMap />
        <Legend />
      </main>
      <aside className="w-[380px] border-l border-white/10 bg-[#0f1422] overflow-y-auto">
        <RegionPanel />
      </aside>
    </div>
  );
}
