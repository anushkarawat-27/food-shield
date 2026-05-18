import "./globals.css";
import "mapbox-gl/dist/mapbox-gl.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "FoodShield",
  description: "Food crisis simulation and decision-support platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
