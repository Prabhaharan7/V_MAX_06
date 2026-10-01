# 🛡️ SIF Sentinel AI — Serious Injury & Fatality Precursor Intelligence

[![SIH 2026](https://img.shields.io/badge/SIH%202026-PS%2026165-FF9900.svg)](https://www.sih.gov.in/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![pgvector](https://img.shields.io/badge/pgvector-pg16-336791.svg)](https://github.com/pgvector/pgvector)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-v3-38B2AC.svg)](https://tailwindcss.com/)

> **Smart India Hackathon (SIH 2026) — Problem Statement PS 26165**  
> **Target Organization:** Oil India Limited  
> **Domain:** Upstream Exploration & Production Safety, Near-Miss NLP Mining & Precursor Detection.

---

## 📌 Executive Summary

**SIF Sentinel AI** is an industrial AI/NLP intelligence engine engineered to detect and prevent **Serious Injury & Fatality (SIF) precursors** from unstructured safety observation cards, near-miss reports, hazard logs, and daily drilling reports across Oil India's operational assets in Assam, Rajasthan, and the KG Basin.

By combining domain-specific oilfield NLP extraction, 9 IOGP Life-Saving Rules (LSR) multi-label taggers, and 384-dimensional vector similarity search with PostgreSQL `pgvector`, SIF Sentinel AI surfaces critical low-frequency/high-severity signals (such as well kicks, high-pressure energy releases, toxic gas leaks, and rigging failures) before they result in catastrophic incidents.

---

## 👥 Demo User Logins (Role-Based Access)

Use these pre-seeded credentials to evaluate the platform from different operational perspectives:

| Role | Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **HSE Officer** | `pranab.hse@oilindia.in` | `OilIndia@2026` | Full Control Room Dashboard, Safety Memory, Review Queue triage, Pattern Mining. |
| **Site Manager** | `arun.manager@oilindia.in` | `OilIndia@2026` | Asset-specific safety metrics, Rig 14 field reports, and local barrier alerts. |
| **HQ Admin** | `admin@oilindia.in` | `Admin@2026` | Enterprise user management, NLP model calibration, and audit logging. |

> 💡 **Fast Persona Switching**: The Login Page features one-click demo persona chips to instantly authenticate as any role without manual typing.

---

## 🏗️ Architecture & Monorepo Structure

```text
PS165/
├── .env.example               # Template environment variables
├── .env                       # Local environment configuration
├── docker-compose.yml         # Zero-config multi-container orchestration
├── docker/
│   └── init-db.sql            # Postgres init script (enables pgvector & uuid-ossp)
├── backend/                   # FastAPI application (Python 3.11)
│   ├── alembic/               # Async database migrations
│   ├── app/
│   │   ├── api/               # API endpoints (auth, reports, patterns, health)
│   │   ├── core/              # Config, Async SQLAlchemy 2.0 database, JWT security
│   │   ├── ml/                # Hybrid SIF Classifier & 9 IOGP LSR Tagging engine
│   │   ├── models/            # Relational models with Vector(384) columns
│   │   ├── schemas/           # Pydantic v2 validation models
│   │   ├── services/          # Pattern mining & NLP pipeline orchestration
│   │   └── main.py            # FastAPI entrypoint with auto-seeding lifespan
│   ├── scripts/
│   │   └── seed_data.py       # 300 realistic oilfield reports + 10 fatality cases
│   ├── tests/                 # 16 unit tests for ML, Tagging & Pattern Mining
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/                  # React 18 + TypeScript + Vite + Tailwind + Recharts
    ├── src/
    │   ├── components/        # AppShell, ProtectedRoute, UI components
    │   ├── context/           # AuthContext (JWT session management)
    │   ├── pages/             # Dashboard, SubmitReport, ReviewQueue, Alerts, Sites, Settings
    │   ├── App.tsx            # React Router navigation tree
    │   └── index.css          # Industrial dark control-room theme
    ├── Dockerfile
    └── package.json
```

---

## 🚀 Quickstart with Docker Compose

### Prerequisites
- [Docker Desktop / Docker Engine](https://docs.docker.com/get-docker/) installed and running.

### 1. Start the entire platform
Run from the repository root:

```bash
docker compose up --build
```

*(Everything starts cleanly with zero manual steps: database extensions, tables, demo users, and 300 synthetic reports are auto-initialized on first launch).*

### 2. Access the Application Services

| Service | URL | Description |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost:5173](http://localhost:5173) | Industrial SIF Sentinel Control Room UI |
| **Backend Swagger API** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive OpenAPI documentation |
| **Health Check Endpoint** | [http://localhost:8000/api/health](http://localhost:8000/api/health) | Live PostgreSQL & pgvector health status |
| **PostgreSQL + pgvector** | `localhost:5432` | Database `sif_sentinel` (user: `postgres`, pass: `postgres`) |

---

## 🧪 Local Development & Test Execution

### Backend Tests
Execute the comprehensive test suite (16 tests covering SIF classification, IOGP tagging, and pattern aggregation):

```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Build
Validate TypeScript typings and build the production bundle:

```bash
cd frontend
npm run build
```

---

## 📜 Problem Statement Compliance
Built specifically for **Smart India Hackathon 2026 (SIH 2026 PS 26165)** for **Oil India Limited**.
