# TALOS — Autonomous Repository Maintenance System

[![Phase 1 Complete](https://img.shields.io/badge/Phase%201-Foundation%20%26%20GitHub%20Integration-blue.svg)](#)
[![Stack](https://img.shields.io/badge/Tech%20Stack-FastAPI%20%7C%20React%20%7C%20PostgreSQL%20%7C%20Docker-brightgreen.svg)](#)

TALOS is an autonomous repository maintenance system. It continuously monitors software repositories, detects routine maintenance problems, understands what needs to change, creates isolated fixes, verifies those fixes through real engineering checks, and delivers review-ready pull requests.

---

## Workflow Overview

```text
WATCH  ──►  DETECT  ──►  UNDERSTAND  ──►  PLAN  ──►  PATCH  ──►  VERIFY  ──►  DELIVER
                                                                                │
                                                                                ▼
                                                                       HUMAN REVIEW & MERGE
```

---

## Phase 1 Deliverables

Phase 1 establishes the core platform foundation:
1. **GitHub Connection Service**: Connect GitHub using Personal Access Tokens (PAT) or GitHub OAuth App flow.
2. **Repository Metadata Sync**: Fetches and stores owner, repository name, default branch, primary language, visibility, clone URL, HTML URL, and latest commit info (SHA, message, author, date).
3. **Database Relational Architecture**: PostgreSQL schema with models for `User`, `GitHubConnection`, `Repository`, and stubs for future entities (`MaintenanceIssue`, `MaintenanceJob`, `PatchAttempt`, `VerificationRun`, `ActionLog`, `PullRequest`).
4. **Operations Dashboard**: Modern developer infrastructure interface built with React + TypeScript (Vercel/Linear/GitHub dark style).
5. **Repository Detail Page**: Inspect repository status, commit history, sync metadata, toggle monitoring state, and view clearly labeled future phase modules.
6. **Container Orchestration**: Production-conscious `docker-compose.yml` orchestrating `postgres`, `backend`, and `frontend`.

---

## Tech Stack

* **Frontend**: React 18, TypeScript, Vite, Lucide Icons, Custom Developer Dark Theme
* **Backend**: FastAPI, Python 3.11, Async SQLAlchemy 2.0, Pydantic v2, HTTPX
* **Database**: PostgreSQL 16
* **Infrastructure**: Docker & Docker Compose

---

## Project Structure

```text
talos/
├── frontend/             # Vite + React + TypeScript Dashboard
│   ├── src/
│   │   ├── components/   # Sidebar, Header, MetricsOverview, RepositoryCard, ConnectGithubModal
│   │   ├── pages/        # DashboardPage, RepositoryDetailPage, ActivityPage, SettingsPage
│   │   ├── services/     # Typed API Client
│   │   ├── types/        # TypeScript Interfaces
│   │   └── index.css     # Developer Infrastructure Theme
│   └── Dockerfile
├── backend/              # FastAPI Python Service
│   ├── app/
│   │   ├── api/v1/       # REST Routes (Auth, Repositories, Health)
│   │   ├── core/         # Security, Configuration, JWT
│   │   ├── db/           # Async SQLAlchemy Engine & Base
│   │   ├── models/       # Relational Database Models
│   │   ├── schemas/      # Pydantic Input/Output Validation
│   │   └── services/     # GitHub REST API & Repository Business Logic
│   └── Dockerfile
├── worker/               # Background Worker Architecture (Prepared for Phase 2+)
├── docker-compose.yml    # Orchestration for PostgreSQL, Backend, Frontend
├── .env.example          # Environment Variables Template
└── README.md
```

---

## Quickstart & How to Run

### Option A: Using Docker Compose (Recommended)

1. Clone or navigate to the repository directory:
   ```bash
   cd /path/to/talos
   ```

2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Launch all containers:
   ```bash
   docker compose up --build
   ```

4. Access the applications:
   - **TALOS Operations Dashboard**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Running Locally Outside Docker

#### 1. Start PostgreSQL
Ensure PostgreSQL is running locally on port 5432 with database `talos_db` and credentials `talos` / `talos_secret_pass`.

#### 2. Start Backend Service
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 3. Start Frontend App
```bash
cd frontend
npm install
npm run dev
```

---

## Required Environment Variables

Key environment variables in `.env`:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PROJECT_NAME` | Application Name | `TALOS` |
| `SECRET_KEY` | JWT signing secret | `talos-super-secret-key-...` |
| `POSTGRES_SERVER` | Postgres DB hostname | `postgres` (or `localhost`) |
| `POSTGRES_PORT` | Postgres DB port | `5432` |
| `POSTGRES_USER` | Postgres DB username | `talos` |
| `POSTGRES_PASSWORD` | Postgres DB password | `talos_secret_pass` |
| `POSTGRES_DB` | Postgres DB name | `talos_db` |
| `GITHUB_CLIENT_ID` | Optional GitHub OAuth Client ID | `""` |
| `GITHUB_CLIENT_SECRET` | Optional GitHub OAuth Secret | `""` |

---

## Verification & Testing

To test the complete flow:
1. Open the dashboard at `http://localhost:3000`.
2. Click **Connect Repository** (or navigate to Settings).
3. Enter a GitHub Personal Access Token (PAT) with `repo` permissions.
4. Select a repository from the retrieved GitHub list and click **Connect**.
5. Observe the repository card appear on the dashboard with real language, default branch, and latest commit info.
6. Click **View** to inspect real GitHub metadata on the Repository Detail Page.
