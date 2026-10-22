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

## Deploy

- **Backend (Render):** the repo root contains `render.yaml`. Create a
  Render account → New → Blueprint → select the EdgeMind repo. Set
  `EDGEMIND_CORS_ORIGINS` to the Vercel URL after the frontend deploys.
- **Frontend (Vercel):** New Project → import the repo → set root
  directory to `edgemind-ui` → add env var `VITE_API_URL` pointing at
  the Render URL (e.g. `https://edgemind-api.onrender.com`) → Deploy.

Free-tier note: Render's free plan sleeps when idle; first interaction
after idle can take ~30–60 s (cold start).
