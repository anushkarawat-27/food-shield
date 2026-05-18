"use client";

const ITEMS: { label: string; color: string }[] = [
  { label: "Drought", color: "#f59e0b" },
  { label: "Flood", color: "#3b82f6" },
  { label: "Heat", color: "#ef4444" },
  { label: "Pest", color: "#a855f7" },
  { label: "Frost", color: "#22d3ee" },
];

export default function Legend() {
  return (
    <div className="absolute bottom-4 left-4 z-10 bg-[#0f1422]/90 border border-white/10 rounded-md px-3 py-2 text-xs">
      <div className="opacity-70 mb-1">Live disruptors (30d)</div>
      <ul className="space-y-1">
        {ITEMS.map((i) => (
          <li key={i.label} className="flex items-center gap-2">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: i.color }}
            />
            {i.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
