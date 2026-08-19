# ConsultBae AI Automation & Data Processing System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask 3.0](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.org/)
[![n8n Automation](https://img.shields.io/badge/n8n-Automation-FF6D5A?style=flat&logo=n8n&logoColor=white)](https://n8n.io)
[![FFmpeg Engine](https://img.shields.io/badge/FFmpeg-Audio%20Engine-0078D7?style=flat&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![SQLite Master DB](https://img.shields.io/badge/SQLite-Database-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)

Implementation of the candidate ingestion pipeline, workflow automation, audio processing web application, data quality audit, and system scaling architecture for the ConsultBae AI Automation Assignment.

---

## Executive Summary

This repository delivers an end-to-end data processing and automation platform built across five core assignment tasks:

1. **Multi-Tier Entity Resolution ETL Pipeline**: Disjoint Set Union (DSU) graph algorithm resolving candidate profiles across three heterogeneous sources into a unified SQLite schema.
2. **Workflow Automation & AI Skill Categorization**: Production-grade n8n workflow implementing duplicate detection alerts and automated LLM skill classification.
3. **Gig Worker Audio Collection Portal**: Web application featuring real-time audio visualization, state-machine recording controls (Record, Pause, Resume, Reset), and an FFmpeg/FFprobe audio quality extraction engine.
4. **Data Quality Audit**: Granular audit report cataloging 12 planted anomalies across raw CSV inputs with line and row references.
5. **System Scaling Blueprint**: Architectural analysis for scaling audio collection to 5,000 concurrent gig workers with presigned object storage uploads and an itemized infrastructure cost model.

---

## Video Walkthrough

- **Loom Recording**: `[Insert Video Walkthrough URL Here]`
- **Walkthrough Guide & Script**: Refer to [`docs/VIDEO_WALKTHROUGH_GUIDE.md`](docs/VIDEO_WALKTHROUGH_GUIDE.md) for the minute-by-minute demonstration script.

---

## Task Implementations & File Links

### Task 1: Multi-Source Data Ingestion & Entity Resolution

- **Primary Pipeline Script**: [`pipeline/ingest.py`](pipeline/ingest.py)
- **Cleaning & Normalization Utilities**: [`pipeline/clean_utils.py`](pipeline/clean_utils.py)
- **Database Schema**: [`database/schema.sql`](database/schema.sql)
- **Deduplicated Output Dataset**: [`data/processed/consultbae_merged_candidates.csv`](data/processed/consultbae_merged_candidates.csv)

#### Implementation Details
- Uses a Disjoint Set Union (DSU) Connected Components algorithm to handle multi-hop transitive matching ($A=B$ and $B=C \Rightarrow A=C$).
- Normalizes phone numbers to standard 10-digit formats, emails to lowercase, CTC to Lakhs Per Annum (LPA), and dates to ISO 8601 (`YYYY-MM-DD`).
- Detects structural anomalies such as shifted CSV columns and embedded duplicate headers.
- Reduces **103 raw input records** across three sources to **55 clean canonical candidate records**.

---

### Task 2: n8n Workflow Automation & AI Intelligence

- **Importable n8n JSON Configuration**: [`n8n/consultbae_automation_workflow.json`](n8n/consultbae_automation_workflow.json)
- **Execution & Simulation Script**: [`n8n/run_n8n_simulation.py`](n8n/run_n8n_simulation.py)

#### Implementation Details
- Configured across 10 functional nodes handling webhook ingestion, database queries, duplicate alert routing, and LLM skill categorization.
- Uses local API endpoints (`http://localhost:8000/api/...`) for local testing.
- Outputs structured JSON arrays containing candidate skill tags (e.g., `["automation-heavy", "python", "data-engineering"]`).

---

### Task 3: Mini Audio Collection Web Application

- **Application Server**: [`app/server.py`](app/server.py)
- **Audio Processing Engine**: [`app/services/audio_processor.py`](app/services/audio_processor.py)
- **Database Service Layer**: [`app/services/db_service.py`](app/services/db_service.py)
- **User Interface (HTML/CSS/JS)**: [`app/static/index.html`](app/static/index.html), [`app/static/css/style.css`](app/static/css/style.css), [`app/static/js/app.js`](app/static/js/app.js)

#### Implementation Details
- Provides a dark-themed browser interface with an interactive canvas frequency equalizer and millisecond-accurate timer.
- Supports live audio recording with **Record**, **Pause**, **Resume**, and **Reset** controls, as well as file upload functionality.
- Integrates `ffprobe` and `ffmpeg` CLI filters to extract Duration (seconds), Sample Rate (kHz), Bitrate (kbps), Integrated Loudness (dB LUFS via EBU R128), and Signal-to-Noise Ratio (SNR).
- Includes stderr log parsing fallbacks to extract accurate durations for browser WebM files lacking header metadata.

---

### Task 4: Data Quality Audit Report

- **Detailed Audit Documentation**: [`docs/DATA_ISSUES_REPORT.md`](docs/DATA_ISSUES_REPORT.md)
- **Structured Audit CSV Log**: [`data/processed/data_issues_log.csv`](data/processed/data_issues_log.csv)

#### Implementation Details
- Documents 12 distinct data quality anomalies identified across raw inputs (`source1_naukri_applicants.csv`, `source2_gig_workers.csv`, and `source3_cbnexus_contacts.csv`).
- Details specific resolution logic for shifted columns (Row 19), embedded headers (Line 16), CTC currency discrepancies, name abbreviations, and heterogeneous boolean fields.

---

### Task 5: System Scaling Analysis (5,000 Gig Worker Launch)

- **Architectural Analysis Documentation**: [`docs/STRETCH_SCALING_ANALYSIS.md`](docs/STRETCH_SCALING_ANALYSIS.md)

#### Implementation Details
- Evaluates five critical failure modes under high concurrency: thread pool saturation, local disk exhaustion, synchronous FFmpeg CPU locks, SQLite database locking, and mobile network race conditions.
- Proposes a production cloud architecture utilizing Cloudflare CDN, load balancing, stateless API containers, direct-to-S3 presigned uploads, Redis/Celery task queues, and managed PostgreSQL.
- Includes an itemized infrastructure cost analysis demonstrating support for 5,000 weekend workers for under $10.00 total cloud expenditure.

---

## Directory Structure

```
.
├── app/                        # Task 3: Flask Web Portal & FFmpeg Engine
│   ├── server.py               # Main Flask API Server
│   ├── services/               # Audio Processing & Database Services
│   └── static/                 # Frontend Web Assets (HTML, CSS, JS)
├── data/
│   ├── raw/                    # Raw Input CSV Files
│   └── processed/              # Cleaned Datasets & Audit Logs
├── database/
│   ├── schema.sql              # Master SQLite Schema Definition
│   └── consultbae.db           # Ingested SQLite Database File
├── docs/                       # Project Documentation & Task Reports
│   ├── DATA_ISSUES_REPORT.md      # Task 4 Data Audit Report
│   ├── STRETCH_SCALING_ANALYSIS.md# Task 5 Scaling Analysis
│   └── VIDEO_WALKTHROUGH_GUIDE.md # Video Walkthrough Script
├── n8n/                        # Task 2: Automation Workflow & Simulation
│   ├── consultbae_automation_workflow.json
│   └── run_n8n_simulation.py
├── pipeline/                   # Task 1: Data Ingestion & Entity Resolution
│   ├── clean_utils.py          # Data Normalization Functions
│   └── ingest.py               # DSU Pipeline Execution Script
├── tests/                      # Automated Test Suite
│   └── test_all.py             # pytest Test Cases
└── requirements.txt            # Python Dependencies
```

---

## Getting Started

### 1. Installation & Environment Setup

```bash
# Clone the repository
git clone https://github.com/SamirXR/ConsultBae-Assignment.git
cd ConsultBae-Assignment

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements and system dependencies
pip install -r requirements.txt
sudo apt-get install -y ffmpeg
```

### 2. Ingestion Pipeline Execution (Task 1)

```bash
python3 pipeline/ingest.py
```

Runs the DSU entity resolution pipeline to clean raw CSV files and generate `database/consultbae.db`.

### 3. Application Server Execution (Task 3)

```bash
python3 app/server.py
```

Starts the local Flask web server at `http://localhost:8000`.

### 3b. Deploy to Render

This repo includes a [`render.yaml`](render.yaml) and [`Procfile`](Procfile) so you can create a Render Web Service directly from the GitHub repo.

Use these settings if you deploy manually:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app.server:app`
- Health check path: `/`

The app uses SQLite at `database/consultbae.db`, so a Render deployment will work for demo/testing, but data will be lost on restarts unless you add persistent storage or move the database to an external managed service.

### 4. Workflow Simulation (Task 2)

```bash
python3 n8n/run_n8n_simulation.py
```

Simulates candidate ingestion webhooks, duplicate detection checks, and LLM skill classification.

### 5. Automated Test Suite Execution

```bash
python3 -m unittest discover tests
```

Runs all 51 automated unit and integration tests across data processing, database operations, and audio metadata logic.

---

## License

Submitted for evaluation under the ConsultBae Recruitment Assessment.
