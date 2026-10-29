# Football Super Intelligence frontend

A standalone React + TypeScript match workspace. All source, dependencies, imported replay data and generated build output are contained in this directory. No backend changes are required for local replay.

## Run

Requires Node.js 22.12+ (tested on Node 24).

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (usually http://127.0.0.1:5173).

```powershell
npm test
npm run build
npm run preview
```

## Included experiences

- Match overview with Coach, Analyst, Broadcast and Fan adaptations.
- Synchronized replay, time scrubbing, speed selection, goals, shots, xG and passing totals.
- Interactive 2D pitch, selected player, ball trail and 3-unit proximity radius.
- Mean recorded passer pressure by five-minute window.
- Player contribution table, event filters, source evidence inspection and moment navigation.
- Foundry intelligence studio calling the existing three-agent workflow.
- API connection settings, health check and separate API statistics snapshot.
- JSON report download, responsive navigation and system capability roadmap.

## Data and interpretation

`public/data/replay.json` is a compact copy of the repository's synthetic Footysim run `426b7bce-2df0-47fc-b50f-16eb35a094db`. It contains all 3,051 canonical events and 1,081 tracking frames sampled every five seconds. `scripts/prepare-data.mjs` can regenerate it by reading that run without changing the original files. The application does not read files outside frontend at runtime.

Every local metric excludes events after the selected cutoff. Pass attempts and completions use separate `pass` and `pass_complete` events; xG sums `shot` events only. Pressure is the average non-null `pressure` on pass attempts, not a validated causal pressing metric. Player contribution is an action count, not a performance rating. Pitch distances remain source coordinate units. Shirt numbers are display indices, not source squad numbers. Missing values remain unavailable.

Local summaries are deterministic descriptions, explicitly labelled. They do not impersonate Foundry output. The local replay is not connected to Fabric or a live WebSocket. Agent responses are rendered as plain text.

## Existing API integration

Start the project's existing FastAPI service separately with its required Azure/Fabric environment and authentication. This frontend does not start or configure it. In Workspace Settings, the default `/fsi-api` uses Vite's proxy to `http://127.0.0.1:8000`, avoiding a backend CORS change in development.

Supported routes:

| Action | Existing route |
| --- | --- |
| Health | `GET /health` |
| Statistics | `GET /api/v1/matches/{run_id}/stats?as_of_second=…` |
| Agent workflow | `POST /api/v1/intelligence/analyse` |

The request body includes `run_id`, `as_of_second` (0–5400), `fan_level` (`beginner`, `enthusiast`, `advanced`) and `preferred_team` (`BLU`, `RED`). Analysis responses use `coach`, `broadcast`, `fan`, `run_id` and `as_of_second`.

Connection settings are stored locally after a successful request. No credentials or secrets belong in frontend configuration. Requests have timeouts (15 seconds for health/stats, two minutes for agents) and explicit error states. API statistics remain separate from local replay because event/tracking endpoints are not exposed by the current backend.

For production, serve `dist/` on a static host and route `/fsi-api/*` to the existing API with the prefix removed, or supply an absolute API base URL in Settings with appropriate backend CORS support. Vite's development proxy is not part of the production bundle. Google Fonts are optional; system sans-serif fonts are the fallback.

## Planned capabilities

The roadmap labels WebSocket streaming, reconnect handling, persistent insight history, additional languages, telemetry, Football Manager support and hosted acceptance checks as planned. There are no fabricated cloud health states or simulated AI results.

