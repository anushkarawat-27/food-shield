"use client";

import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useStore } from "@/lib/store";
import { getEventsGeoJSON, getRegionsGeoJSON } from "@/lib/api";

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

export default function WorldMap() {
  const ref = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const impacts = useStore((s) => s.impacts);
  const setSelectedRegion = useStore((s) => s.setSelectedRegion);

  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    if (!TOKEN) {
      // Map needs a token; show a placeholder rather than crashing.
      return;
    }
    mapboxgl.accessToken = TOKEN;
    const map = new mapboxgl.Map({
      container: ref.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [20, 10],
      zoom: 1.6,
    });
    mapRef.current = map;

    map.on("load", async () => {
      try {
        const fc = await getRegionsGeoJSON(0);
        map.addSource("regions", { type: "geojson", data: fc });
        map.addLayer({
          id: "regions-fill",
          type: "fill",
          source: "regions",
          paint: {
            "fill-color": [
              "case",
              ["has", ["to-string", ["id"]], ["literal", {}]],
              "#1e7d50",
              "#1f2a40",
            ],
            "fill-opacity": 0.55,
          },
        });
        map.addLayer({
          id: "regions-line",
          type: "line",
          source: "regions",
          paint: { "line-color": "#3d4763", "line-width": 0.5 },
        });
        map.on("click", "regions-fill", (e) => {
          const f = e.features?.[0];
          if (f && f.id != null) setSelectedRegion(Number(f.id));
        });

        // Live disruptor events overlay
        try {
          const events = await getEventsGeoJSON(30);
          map.addSource("events", { type: "geojson", data: events });
          map.addLayer({
            id: "events-circles",
            type: "circle",
            source: "events",
            paint: {
              "circle-radius": [
                "interpolate", ["linear"], ["get", "severity"],
                0, 3, 1, 10,
              ],
              "circle-color": [
                "match", ["get", "disruptor_type"],
                "drought", "#f59e0b",
                "flood",   "#3b82f6",
                "heat",    "#ef4444",
                "pest",    "#a855f7",
                "frost",   "#22d3ee",
                "#9ca3af",
              ],
              "circle-opacity": 0.75,
              "circle-stroke-color": "#0b0f1a",
              "circle-stroke-width": 1,
            },
          });
          map.on("click", "events-circles", (e) => {
            const f = e.features?.[0];
            if (!f) return;
            const p = f.properties as any;
            new mapboxgl.Popup()
              .setLngLat((e.lngLat as any))
              .setHTML(
                `<div style="color:#111;font-size:12px">
                  <b>${p.disruptor_type}</b> (${p.source})<br/>
                  severity: ${Number(p.severity).toFixed(2)}<br/>
                  ${p.started_at}
                </div>`,
              )
              .addTo(map);
          });
          map.on("mouseenter", "events-circles", () => {
            map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", "events-circles", () => {
            map.getCanvas().style.cursor = "";
          });
        } catch (e) {
          console.warn("events overlay skipped", e);
        }
      } catch (e) {
        console.warn("regions not loaded — seed the DB first", e);
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [setSelectedRegion]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;
    if (!map.getLayer("regions-fill")) return;
    // Color regions by yield_delta_pct: deeper red = worse impact.
    const stops: any[] = ["match", ["to-number", ["id"]]];
    for (const r of Object.values(impacts)) {
      const v = Math.max(-90, Math.min(0, r.yield_delta_pct));
      const t = -v / 90; // 0..1
      const red = Math.round(255 * t);
      const green = Math.round(180 * (1 - t));
      stops.push(r.region_id, `rgb(${red}, ${green}, 80)`);
    }
    stops.push("#1f2a40");
    map.setPaintProperty("regions-fill", "fill-color", stops as any);
  }, [impacts]);

  if (!TOKEN) {
    return (
      <div className="flex h-full items-center justify-center text-sm opacity-60 px-8 text-center">
        Set <code className="mx-1">MAPBOX_TOKEN</code> in .env to render the world map.
      </div>
    );
  }
  return <div ref={ref} className="absolute inset-0" style={{ width: "100%", height: "100%" }} />;
}
