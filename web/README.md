# LiveLift — Bàn trung control (web)

Next.js 14 (App Router) + TypeScript + Tailwind + Recharts dashboard for the
LiveLift live-commerce experimentation platform (AISC'26).

## Pages

| Route | Screen |
|---|---|
| `/` | Bàn trung control — three zones: session rhythm + switchback block strip (top), action cards (bottom-left), comment radar + feed (bottom-right). Dark, Vietnamese UI, designed for 1920x1080 without scrolling. |
| `/host` | **Blinded** host screen (rule L6): pinned product name, price, stock, and total elapsed time only — no block boundaries, no ON/OFF assignment, no per-block countdown. |
| `/replay` | Replay Engine: plays an ended session's recorded ticks/comments/cards through the same three-zone layout, with play/pause, 1x/4x/16x speed, a scrubber, and a what-if panel ("hết hàng" per product re-ranks the action cards client-side). |

## Dev commands

```bash
cd web
npm install        # once
npm run dev        # http://localhost:3000
npm run build      # production build (type-checks)
npm run start      # serve the production build
npm run lint
```

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI backend base URL (REST + `/ws/{session_id}` WebSocket). |
| `NEXT_PUBLIC_PUBLIC_API_BASE` | unset | PUBLIC base URL for the `/r/{code}` measurement links shown to paste into the pinned comment — viewers' phones must reach it (real domain or tunnel). Falls back to `NEXT_PUBLIC_API_BASE`, then `NEXT_PUBLIC_API_URL`. |
| `NEXT_PUBLIC_MOCK` | unset | Set to `1` to force mock mode (see below). |

See `.env.example` for a commented template (copy to `.env.local`).

## Mock mode ("DEMO DATA")

The desk can demo fully standalone. Mock mode activates in either case:

1. `NEXT_PUBLIC_MOCK=1` at build/dev time, or
2. the API is unreachable — every page probes `GET /sessions` once on load
   (2.5 s timeout) and falls back automatically.

In mock mode the hooks (`useDesk`, `useHost`, `useReplay`) serve a
deterministic client-side recording (`src/lib/mock.ts`, seeded PRNG so demos
replay identically), driven by an accelerated demo clock, and every page shows
the yellow **DEMO DATA** badge (the hooks report `connection === "mock"`).
Live mode instead polls REST every 5 s and layers WebSocket pushes on top.

```bash
# Windows (PowerShell)
$env:NEXT_PUBLIC_MOCK = "1"; npm run dev
# POSIX
NEXT_PUBLIC_MOCK=1 npm run dev
```

## Project rules encoded in the UI

- **E2-04** — a card with `source="forecast"` gets a gray "Ước lượng dự báo"
  badge and NEVER renders a confidence interval (`api.sanitizeCard` strips CI
  fields defensively; `ActionCard` guards again). Only `source="experiment"`
  cards show the green "Tác động đo được · KTC 95%" badge with
  `[ci_low, ci_high]`.
- **L6 blinding** — `/host` renders only the `HostState` boundary type
  (`src/lib/types.ts`); the block strip is operator-only.
- **Overrides** — manual override reasons are restricted to
  `hết hàng | sai giá | sự cố kỹ thuật`.
- Numbers/time use the `vi-VN` locale (`src/lib/format.ts`, display timezone
  Asia/Ho_Chi_Minh); animations respect `prefers-reduced-motion`.
