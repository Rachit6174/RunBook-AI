# RunBook AI — Frontend

A React + Vite dashboard for the RunBook AI FastAPI backend.

## Features
- Overview dashboard with incident metrics and charts
- Incident intake connected to `POST /incidents`
- Incident detail drawer with AI remediation plan
- Resolution tracking connected to `POST /incidents/{incident_id}/resolution`
- Learning dashboard with transparent, browser-data-based incident category summaries
- CSV export
- Responsive desktop and mobile layout

## Requirements
- Node.js 18+ (Node.js 20 or 22 recommended)
- Existing RunBook AI FastAPI backend running on port 8000

## Setup

From the `frontend` directory:

```bash
npm install
cp .env.example .env
npm run dev
```

Open the Vite URL shown in the terminal, normally:

`http://localhost:5173`

## Backend

In a separate terminal, from the project root:

```bash
python -m uvicorn backend.api:app --reload
```

The frontend calls:

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/incidents`
- `POST http://127.0.0.1:8000/incidents/{incident_id}/resolution`

The backend CORS configuration must allow `http://localhost:5173`. Your current API configuration already includes this origin.

## Important data notes
- The dashboard starts with three clearly labelled demo records so the interface is populated on first launch.
- Live incidents submitted through the UI are saved in browser localStorage for this browser profile.
- The backend remains the source of truth for server-side incident and resolution storage.
- This frontend does not yet call a backend list/history endpoint. Add a protected `GET /incidents` endpoint before treating the dashboard as a shared, multi-user incident console.
- Learning category counts are heuristic keyword groupings of the records currently visible in this browser. They are not claimed to be Hindsight recall results or verified root-cause analytics.
- Demo records cannot be submitted as real resolutions.
- AI-generated remediation plans are advisory. A human engineer must validate recommendations and approve production actions.

## Production hardening still required
- Authentication and authorization
- Server-side incident listing and pagination
- Shared user/team identity and audit trail
- Rate limiting and request logging
- Secure deployment of secrets (never put Groq or Hindsight keys in frontend variables)
- Verified incident resolution workflow and post-incident review
