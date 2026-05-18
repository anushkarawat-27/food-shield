import { create } from "zustand";
import type { Scenario, RegionInputs } from "./api";

const DEFAULT_INPUTS: RegionInputs = { drought: 0, flood: 0, heat: 0, pest: 0, frost: 0 };

type ImpactRow = { region_id: number; yield_delta_pct: number; affected_population: number };

type State = {
  selectedRegionId: number | null;
  scenario: Scenario;
  impacts: Record<number, ImpactRow>;
  setSelectedRegion: (id: number | null) => void;
  setInput: (regionId: number, key: keyof RegionInputs, value: number) => void;
  setImpacts: (rows: ImpactRow[]) => void;
  reset: () => void;
};

export const useStore = create<State>((set) => ({
  selectedRegionId: null,
  scenario: {},
  impacts: {},
  setSelectedRegion: (id) => set({ selectedRegionId: id }),
  setInput: (regionId, key, value) =>
    set((s) => ({
      scenario: {
        ...s.scenario,
        [regionId]: { ...(s.scenario[regionId] ?? DEFAULT_INPUTS), [key]: value },
      },
    })),
  setImpacts: (rows) =>
    set({ impacts: Object.fromEntries(rows.map((r) => [r.region_id, r])) }),
  reset: () => set({ scenario: {}, impacts: {}, selectedRegionId: null }),
}));

export { DEFAULT_INPUTS };
