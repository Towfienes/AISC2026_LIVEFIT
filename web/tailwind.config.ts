import type { Config } from "tailwindcss";

/**
 * LiveLift control-desk theme — committed dark look.
 * Chart/ink tokens follow the validated dataviz reference palette (dark column).
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        page: "#0d0d0d", // page plane
        surface: "#1a1a19", // chart / card surface
        raised: "#232322", // elevated surface (tooltips, chips)
        ink: "#ffffff", // primary ink
        sec: "#c3c2b7", // secondary ink
        mut: "#898781", // muted (axis, labels)
        muted: "#898781", // alias — some components use text-muted
        grid: "#2c2c2a", // hairline gridline
        axis: "#383835", // baseline / axis / neutral fill
        s1: "#3987e5", // categorical slot 1 — blue
        s2: "#d95926", // slot 2 — orange
        s3: "#199e70", // slot 3 — aqua
        s4: "#c98500", // slot 4 — yellow
        s5: "#d55181", // slot 5 — magenta
        s6: "#008300", // slot 6 — green
        s7: "#9085e9", // slot 7 — violet (block strip ON)
        good: "#0ca30c",
        warn: "#fab219",
        serious: "#ec835a",
        critical: "#d03b3b",
      },
      borderColor: {
        hairline: "rgba(255,255,255,0.10)",
        edge: "rgba(255,255,255,0.10)", // alias — some components use border-edge
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
