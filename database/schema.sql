-- ConsultBae Unified Database Schema (SQLite)

DROP TABLE IF EXISTS audio_submissions;
DROP TABLE IF EXISTS field_conflicts;
DROP TABLE IF EXISTS automation_logs;
DROP TABLE IF EXISTS candidates;
DROP TABLE IF EXISTS raw_naukri_applicants;
DROP TABLE IF EXISTS raw_gig_workers;
DROP TABLE IF EXISTS raw_cbnexus_contacts;

-- Master Deduplicated Candidates Table
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT,
    alt_email TEXT,
    phone TEXT,
    city TEXT,
    experience_years REAL,
    ctc_lpa REAL,                      -- Standardized Current CTC in Lakhs Per Annum (LPA)
    applied_date TEXT,                  -- Standardized ISO Format (YYYY-MM-DD)
    gig_rate TEXT,                      -- Original rate string e.g. "1415/hr", "72k/month"
    gig_rate_num REAL,                  -- Extracted numeric value
    gig_rate_unit TEXT,                 -- "hr" or "month"
    gig_status TEXT,                    -- Active, Inactive, Paused
    skills TEXT,                        -- Comma-separated skills
    skill_category TEXT,                -- Auto-tagged by Task 2 LLM workflow
    cbnexus_verified INTEGER DEFAULT 0, -- 1 for Verified, 0 for Unverified
    cbnexus_projects INTEGER DEFAULT 0, -- Count of completed gig projects
    sources_found TEXT,                 -- Lineage e.g. "naukri,gig,cbnexus"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Audio Submissions Table (Task 3)
CREATE TABLE audio_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    submitter_name TEXT NOT NULL,
    phone_number TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT,                     -- SHA-256 hash of audio file for deduplication
    file_size_bytes INTEGER,
    duration_seconds REAL,              -- Duration in seconds
    sample_rate_khz REAL,               -- Sample rate in kHz (e.g. 44.1)
    bitrate_kbps REAL,                  -- Bitrate in kbps
    bitrate_is_derived INTEGER DEFAULT 0, -- 1 if derived from file size / duration
    loudness_db REAL,                   -- Loudness in dB (EBU R128 / RMS)
    noise_quality_estimate TEXT,        -- Rough noise/quality score e.g. "Excellent (SNR > 30dB)"
    snr_db REAL,                        -- Estimated Signal-to-Noise Ratio in dB
    quality_score INTEGER DEFAULT 80,   -- Overall quality score (0-100)
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);

-- Field Conflicts Audit Table
CREATE TABLE field_conflicts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    field_name TEXT NOT NULL,
    source1_val TEXT,
    source2_val TEXT,
    chosen_val TEXT,
    resolution_method TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);

-- Automation Logs & Webhook Audit (Task 2)
CREATE TABLE automation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    event_type TEXT NOT NULL,           -- "duplicate_alert", "llm_skill_tagging"
    skill_category TEXT,
    payload TEXT,                       -- JSON payload
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
);

-- Raw Lineage Tables for Data Audit
CREATE TABLE raw_naukri_applicants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    city TEXT,
    experience TEXT,
    ctc TEXT,
    applied_date TEXT,
    skills TEXT
);

CREATE TABLE raw_gig_workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT,
    worker_name TEXT,
    rate TEXT,
    location TEXT,
    status TEXT,
    skill_tags TEXT
);

CREATE TABLE raw_cbnexus_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone_number TEXT,
    city TEXT,
    verified TEXT,
    projects_completed TEXT
);

-- Indexes for lightning fast lookups & deduplication checks
CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_phone ON candidates(phone);
CREATE INDEX idx_candidates_name ON candidates(full_name);
CREATE INDEX idx_audio_candidate ON audio_submissions(candidate_id);
