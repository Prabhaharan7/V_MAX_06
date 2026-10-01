# 🛡️ SIF Sentinel AI: Complete Features & System Overview

> **A Simple, Non-Technical Guide to Everything We Built**  
> *Targeted for Oil & Gas HSSE Operations (Drilling, Production, Workover, & Pipelines)*

---

## 💡 What is SIF Sentinel in Simple Words?

In heavy industry and oilfield operations (like **Oil India Limited**), field workers and safety officers submit thousands of safety reports every month:
- **Unsafe Acts (UA)** (e.g., someone working without safety harness)
- **Unsafe Conditions (UC)** (e.g., a frayed winch line or missing valve cover)
- **Near Misses** (e.g., a drill pipe slipping and barely missing a crew member)
- **Incidents** (e.g., minor leaks or equipment damage)

### The Problem:
Most of these thousands of reports are routine (low risk), but **hidden inside them are critical "Precursors" to Severe Injuries and Fatalities (SIF)**. Because safety managers are overwhelmed by reading thousands of rows manually, dangerous warning signs get buried until a catastrophic accident happens.

### The Solution:
**SIF Sentinel AI** is an intelligent safety assistant. You drop in historical safety spreadsheets (from any software or format) or submit individual field observations, and the AI immediately:
1. **Identifies if a report is a High-Risk SIF Precursor** with a confidence score.
2. **Tags which IOGP Life-Saving Rule (LSR)** applies (e.g., *Line of Fire*, *Energy Isolation*, *Bypassing Safety Controls*).
3. **Pinpoints exactly which Safety Barrier failed** (e.g., Physical Guard, Interlock, Permit-to-Work).
4. **Benchmarks its own accuracy** against your company's past verified labels.

---

## 🚀 Key Features We Implemented

---

### 1. 🧠 Smart Spreadsheet Parser with Automatic Alias Detection
* **Before:** Spreadsheets were read purely by column position. If a column was slightly out of order or capitalized differently (e.g., `Site` vs `site_id` vs `Location`), the ingestion broke.
* **Now:** 
  - Reads CSV and Excel (`.xlsx`, `.xls`) files by **column name**, ignoring uppercase/lowercase, spaces, and underscores.
  - Recognizes synonyms and real-world oilfield naming variants:
    - *Narrative / Description / Text / Observation* $\rightarrow$ **`raw_text`**
    - *Type / Observation_Type / Category* $\rightarrow$ **`report_type`**
    - *Site / Installation / Rig / Location / Facility* $\rightarrow$ **`site_id`**
    - *Activity / Task / Operation / Work* $\rightarrow$ **`activity`**

---

### 2. 🔍 "Preview & Confirm" Column Mapping Screen
* **How it works:** When you select or drag & drop any spreadsheet, SIF Sentinel does **not** process all rows blindly.
* **What you see:**
  1. **Quick Header & Sample Preview:** Reads the first 5 data rows in milliseconds.
  2. **Auto-Suggestion Table:** Shows each detected column with a snippet of the actual data in row 1.
  3. **Editable Dropdowns:** If a column has an unusual name, you can choose its target field using a dropdown.
  4. **4-Point Safety Checklist:** A visual checklist verifies that the 4 mandatory fields (`raw_text`, `report_type`, `site_id`, `activity`) are accounted for before allowing upload.
  5. **5-Row Raw Data Drawer:** An expandable table lets you review the raw spreadsheet data directly on the page.

---

### 3. 💾 Saved Template Memory (Zero-Touch Re-Uploads)
* **How it works:** Whenever you confirm a column mapping for a new spreadsheet layout, SIF Sentinel computes a unique **fingerprint** of the column headers and saves it in the database.
* **Benefit:** Next week or next month, when you upload another export from the same software, SIF Sentinel recognizes the fingerprint, **auto-applies your saved mapping**, and pre-confirms the upload—no manual adjustments needed!

---

### 4. 🎯 Ground-Truth Ingestion & Model Accuracy Benchmark
* **How it works:** If your uploaded spreadsheet contains historical expert classifications (`SIF_Label`, `Life_Saving_Rule`, `Barrier_Status`, `Actual_Outcome`, `Split`), SIF Sentinel saves these alongside the reports.
* **What it delivers:**
  - Runs the AI on the raw narrative text independently.
  - Compares the AI's predictions against the ground-truth annotations.
  - Computes comprehensive benchmark metrics:
    - **Overall SIF Accuracy %**
    - **Precision, Recall, and F1-Score** for SIF Precursor detection.
    - **Confusion Matrix** (True Positives, False Positives, True Negatives, False Negatives).
    - **Per-Rule Accuracy** for all 9 IOGP Life-Saving Rules.
    - **Train / Validation / Test Split Breakdown** to evaluate generalization.

---

### 5. 📊 Real-Time Batch Ingestion Dashboard & Visual Analytics
After uploading a batch, you get a clean executive dashboard:
* **Stat Cards:**
  - Total Rows Scanned
  - Accepted Rows (passing schema validation)
  - Rejected Rows (with zero-error validation badges)
  - Queued for Background AI Pipeline
* **Accuracy Preview Card:** Displays the benchmark accuracy % and opens an interactive evaluation report modal.
* **Visual Distribution Charts:**
  - Breakdown by **Report Type** (Near Miss, Unsafe Act, Unsafe Condition, Incident).
  - Breakdown by **SIF vs Non-SIF** distribution.
* **Grouped Error Breakdown:** If rows fail validation (e.g., text too short or empty site), errors are grouped by cause with expandable row details instead of an overwhelming 1,000-row list.
* **Download Processed Dataset Button:** Exports a single CSV containing your original fields + AI predictions + ground-truth comparisons with one click.

---

### 6. ⚡ Single Observation Real-Time Ingestion
* Fast form with test presets (*Line of Fire*, *Energy Isolation*, *Routine Housekeeping*).
* Live telemetry banner that polls background AI processing and updates with confidence % and extracted safety barriers in real time.

---

## 🛠️ Architecture & Tech Stack Summary

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, TypeScript, TailwindCSS, Lucide Icons, Recharts | Fast, responsive, dark-mode glassmorphic UI |
| **Backend API** | FastAPI (Python 3.12), Pydantic v2 | High-performance asynchronous REST API |
| **Database** | PostgreSQL + `pgvector` (SQLAlchemy 2.0 Async) | Relational data & 384-dimensional vector similarity |
| **NLP & AI Engine**| spaCy + SentenceTransformers (`all-MiniLM-L6-v2`) | Hybrid rule-based & semantic vector embedding classifier |
| **Test Suite** | Pytest (Asyncio) | 44 automated test suites covering all edge cases |

---

## 📂 File Summary for Future Reference
- Backend API Routes: [`backend/app/api/reports.py`](file:///c:/Prabha/Projects/PS165/backend/app/api/reports.py)
- Ingestion & Mapping Engine: [`backend/app/services/bulk_ingestion.py`](file:///c:/Prabha/Projects/PS165/backend/app/services/bulk_ingestion.py)
- Accuracy Benchmark Engine: [`backend/app/services/dataset_evaluation.py`](file:///c:/Prabha/Projects/PS165/backend/app/services/dataset_evaluation.py)
- Frontend Intake UI: [`frontend/src/pages/SubmitReportPage.tsx`](file:///c:/Prabha/Projects/PS165/frontend/src/pages/SubmitReportPage.tsx)
- Database Entities: [`backend/app/models/entities.py`](file:///c:/Prabha/Projects/PS165/backend/app/models/entities.py)
