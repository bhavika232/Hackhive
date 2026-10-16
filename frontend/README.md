# SENTINEL AI dashboard

Local React + TypeScript dashboard for the existing HackHive FastAPI backend.

## Start locally

Terminal 1, start the backend from its linked worktree:

```powershell
cd C:\Users\Bhavika\Desktop\codes\hackhive\hackhive-backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.api:app --reload
```

Terminal 2, start the frontend:

```powershell
cd C:\Users\Bhavika\Desktop\codes\hackhive\Hackhive\frontend
npm.cmd install
npm.cmd run dev
```

Open `http://127.0.0.1:5173`. The Vite origin is explicitly allowed by backend CORS. The frontend calls the configured backend directly at `http://127.0.0.1:8000` by default. Override the build-time default by copying `.env.example` to `.env.local` and changing `VITE_API_BASE_URL`. The Settings page can override this per browser using local storage.

## Implemented backend workflows

- `GET /health` drives the connected/disconnected status.
- `GET /incidents` supplies the incident feed, metrics, timeline, camera IDs, and filters.
- `GET /incidents/{id}` loads incidents opened by ID when they are not in the current list.
- `PATCH /incidents/{id}/review` persists true-positive/false-positive review actions.
- The current backend returns incidents as an array. Categories remain `person_down`, `tailgating`, and `crowd_incident` in requests and are only humanized for display.
- The backend stores `keyframe_path` as a machine-local filesystem path. The dashboard displays it as text; it does not treat it as a browser URL or load arbitrary local files.

The backend does not expose live camera status, video streaming, evidence-file serving, per-frame people counts, or an endpoint to launch the vision CLI. The overview marks unavailable counts accordingly; video analysis provides a command guide for the existing local vision runner and does not claim to start processing.

Incident data refreshes every 30 seconds. Time-based views use the stored `start_wall_time` interpreted in the browser's local time zone. Invalid incident responses are surfaced instead of replaced with sample data.

## Build

```powershell
npm.cmd run build
```
