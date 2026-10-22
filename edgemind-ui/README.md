# EdgeMind Live Demo UI

React + TypeScript + Tailwind CSS + Recharts frontend for the EdgeMind
scheduling API. Polls `/state` for live node conditions, submits tasks
to `/schedule` + `/execute` for both policies, and compares their
decisions and actual (simulated) latencies side by side.

## Run locally

```sh
# terminal 1: the API (repo root)
uvicorn app.main:app --port 8000

# terminal 2: this UI
cd edgemind-ui
npm install
npm run dev        # http://localhost:5173
```

## Deploy (both on Vercel)

Two Vercel projects from the same repo:

- **Backend (`edgemind-api`):** New Project → import the repo → root
  directory = **repo root** → framework "Other". Vercel serves
  `api/index.py` (FastAPI as a Python serverless function) with
  `vercel.json` rewriting all routes to it. Add env var
  `EDGEMIND_CORS_ORIGINS` = your frontend URL after the frontend deploys.
- **Frontend (`edgemind-ui`):** New Project → import the repo → root
  directory = `edgemind-ui` → env var `VITE_API_URL` = the backend URL
  (e.g. `https://edgemind-api.vercel.app`) → Deploy.

Serverless note: environment state lives in function memory — it
persists while warm and resets on cold start. Fine for a demo; the
research evaluation never uses this path.

Alternative: `render.yaml` (repo root) deploys the same API as a
persistent Docker service on Render if you ever need warm state.
