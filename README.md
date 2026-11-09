# RunBook-AI

### AI-Powered Incident Response & Operational Learning Platform

RunBook-AI is an AI-powered incident management platform that helps engineering teams analyze production incidents, investigate logs and screenshots, generate remediation plans, and retain operational knowledge for future incidents.

It combines AI reasoning with persistent incident memory to help teams move beyond fixing individual incidents and build a continuously improving incident response system.

---

## Features

- **AI Incident Analysis:** Analyze incident descriptions and identify likely root causes.
- **Multimodal Analysis:** Upload screenshots and log files for combined AI investigation.
- **Automated Remediation Plans:** Generate structured investigation steps, mitigation actions, and corrective recommendations.
- **Historical Incident Memory:** Retrieve relevant information from previous incidents using Hindsight.
- **Incident Management:** Record incidents and track their status.
- **Resolution Tracking:** Record incident resolutions for operational learning.
- **Interactive Dashboard:** View incident information and operational insights.
- **API Documentation:** Explore backend endpoints through FastAPI Swagger UI.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | React.js |
| Build Tool | Vite |
| Styling | CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | Python, FastAPI |
| AI Reasoning | Groq |
| Persistent Memory | Hindsight |
| Database | SQLite |

## Project Structure

```text
RunBook-AI/
│
├── backend/
│   ├── api.py
│   ├── agent.py
│   ├── memory.py
│   ├── cli.py
│   └── tests/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── .env.example
│   ├── package.json
│   └── package-lock.json
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Prerequisites

Install the following before running the application:

- Python 3.11 recommended
- Node.js and npm (Node.js 18 or later recommended)
- Git
- A Groq API key
- Hindsight API credentials

You do not need VS Code. Any terminal and code editor will work.

## Installation Guide

### 1. Clone the repository

```bash
git clone https://github.com/dibakar704/my_creation-.git
cd my_creation-
```

### 2. Set up the backend

Create a Python virtual environment:

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the Python dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure backend environment variables

Create a `.env` file in the main project directory.

Copy the contents of `.env.example` into it and enter your own credentials:

```env
GROQ_API_KEY=your_groq_api_key
HINDSIGHT_API_KEY=your_hindsight_api_key
HINDSIGHT_BANK_ID=your_hindsight_bank_id
HINDSIGHT_BASE_URL=your_hindsight_api_url
```

Obtain your credentials from the respective service providers.

**Important:** Never commit or share your `.env` file. Every user must configure their own API credentials.

### 4. Set up the frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install frontend dependencies:

```bash
npm ci
```

Create the frontend environment file:

**macOS / Linux**

```bash
cp .env.example .env
```

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

The frontend `.env` should contain:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

This connects the frontend to the locally running backend.

## Running the Application

Run both services in separate terminals.

### Terminal 1 — Backend

From the main project directory:

```bash
source .venv/bin/activate
python -m uvicorn backend.api:app --reload
```

On Windows PowerShell, activate the environment using:

```powershell
.venv\Scripts\Activate.ps1
```

Then run the same Uvicorn command.

Backend:

http://127.0.0.1:8000

API documentation:

http://127.0.0.1:8000/docs

### Terminal 2 — Frontend

From the main project directory:

```bash
cd frontend
npm run dev
```

Open the application:

http://localhost:5173

Your RunBook-AI application is now running locally.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Backend welcome endpoint |
| GET | `/health` | Health check |
| POST | `/incidents` | Create and analyze an incident |
| POST | `/incidents/multimodal` | Analyze an incident with uploaded files |
| POST | `/incidents/{incident_id}/resolution` | Record an incident resolution |

Explore the interactive API documentation at `/docs`.

## Example Incident

**Incident description:**

```text
Checkout API is returning 503 errors after Redis
connection failures and worker crashes.
```

RunBook-AI can analyze the incident, examine uploaded screenshots and logs, identify potential root causes, and generate a structured remediation plan.

## Troubleshooting

**Backend fails to start**

- Confirm Python 3.11 is installed.
- Activate the virtual environment.
- Install dependencies again using `pip install -r requirements.txt`.
- Check that your backend `.env` is configured.

**Frontend fails to start**

- Confirm Node.js and npm are installed.
- Run `npm ci` inside the frontend directory.
- Check the frontend `.env` configuration.

**Frontend cannot connect to backend**

- Confirm the backend is running on port 8000.
- Verify `VITE_API_BASE_URL`.
- Restart the Vite development server after changing environment variables.

**AI analysis fails**

- Verify your Groq API key.
- Verify your Hindsight credentials and service configuration.
- Check the backend terminal for the detailed error.

## Security

- API credentials must remain in local environment files.
- `.env` files are excluded through `.gitignore`.
- Never publish private API keys or database credentials.
- Each installation should use its own service credentials.

## Current Deployment Model

RunBook-AI currently supports local development and execution.

Each user runs the backend and frontend on their own machine and supplies their own API credentials.

A public hosted deployment requires separately configured hosting and production environment variables.

## Contributing

Contributions, bug reports, and feature suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make your changes.
4. Test your changes.
5. Submit a pull request.

## License

Add a license before distributing the project for reuse. Until a license is added, the repository's default copyright protections apply.

---

**RunBook-AI — Turning incidents into intelligence.**