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

## ⏱️ 90-Second Demo Script (Evaluator Walkthrough)

Follow this structured 90-second workflow to demonstrate the end-to-end intelligence pipeline:

### **Step 1 (0:00 - 0:15) • Single Observation Intake & Explainable AI**
1. Log in as **HSE Officer** (`pranab.hse@oilindia.in`).
2. Navigate to **Submit Report** (`/submit`).
3. Click the preset: **"⚡ Energy Isolation Bypass (SIF)"** or type:
   > *"Technician bypassed lockout tagout on discharge header electrical drive to expedite seal replacement before shift change without notifying control room engineer."*
4. Click **"Submit & Execute SIF AI NLP Pipeline"**.
5. **Observe**: Success toast appears with the assigned Report ID and an active processing spinner. Within seconds, the AI panel displays:
   - **SIF-Potential Precursor Detected** ($92\%$ confidence)
   - **Primary LSR**: `Energy Isolation`
   - **Extracted Barrier Failure**: `Isolation Confirmation (LOTO)` with **High Severity**.

---

### **Step 2 (0:15 - 0:30) • pgvector Safety Memory & Historical Fatality Matching**
1. From the report detail or reports feed, observe the **Safety Memory (pgvector RAG)** section.
2. The 384-dimensional embedding vector automatically retrieves the most semantically relevant historical fatality from Oil India's case library:
   - **Matched Fatality Case**: *Lethal Stored Hydraulic Energy Release during Iron Roughneck Piston Servicing (2019)*.
   - **Shared Root Cause**: *Bypass of mechanical lockout procedures during maintenance*.
   - **Lessons Learned & Recommended Barrier Controls** are automatically highlighted for supervisor intervention.

---

### **Step 3 (0:30 - 0:45) • Executive Site Rankings & Precursor Density**
1. Navigate to **Dashboard** (`/dashboard`).
2. View the **Top Row KPI Cards**:
   - Total Reports: `300+ observations`
   - `% SIF-Potential Precursors`: `~25% density`
   - Active Alerts: `Critical barrier breach signals`
   - Average Safety Index (SII): `82 / 100`.
3. Review the **Sites Ranked by SIF-Precursor Density** (Horizontal Recharts bar chart) and the **Observations by IOGP Life-Saving Rule** chart showing *Energy Isolation* and *Safe Mechanical Lifting* as top vulnerability drivers.

---

### **Step 4 (0:45 - 1:10) • Active Learning Review Queue (Human-in-the-Loop)**
1. Click **Review Queue** (`/review-queue`) in the sidebar.
2. Select an ambiguous field report with borderline confidence ($0.40 \le \text{confidence} \le 0.60$).
3. Click **"Confirm as SIF Precursor"** or **"Mark as Routine / Non-SIF"**.
4. **Observe**: The correction is logged to `model_feedback_log`, continuously calibrating few-shot semantic classifiers via active learning.

---

### **Step 5 (1:10 - 1:30) • 90-Day Rolling Aggregation & SII Trend Improvement**
1. Return to the Dashboard and click **"Recalculate 90d Trends"**.
2. **Observe**: The scheduled pattern mining engine groups safety observations by `(activity, site location, barrier_type)` over a rolling 90-day window.
3. Review the **Top Recurring Precursor Patterns Table** showing trend trajectory arrows (**RISING**, **STABLE**, **FALLING**).
4. Verify that proactive barrier interventions reflect as a **FALLING** trend and an improved site Safety Index (SII).

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
