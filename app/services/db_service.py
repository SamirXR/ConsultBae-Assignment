import os
import sqlite3
import sys

# Ensure pipeline modules are importable
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "pipeline"))
import clean_utils as cu

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "database", "consultbae.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def find_or_create_candidate(full_name, phone_number):
    """
    Looks up existing candidate in Task 1 database by phone or name.
    If not found, creates a new candidate record.
    """
    conn = get_db_connection()
    norm_p = cu.norm_phone(phone_number)
    norm_n = cu.norm_name(full_name)

    # Search by normalized phone first
    row = None
    if norm_p:
        row = conn.execute("SELECT * FROM candidates WHERE phone = ?", (norm_p,)).fetchone()

    # Search by normalized name if phone search returned nothing
    if not row and norm_n:
        row = conn.execute("SELECT * FROM candidates WHERE LOWER(full_name) = LOWER(?)", (norm_n,)).fetchone()

    if row:
        conn.close()
        return dict(row)

    # Create new candidate record
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO candidates (full_name, phone, sources_found)
        VALUES (?, ?, 'audio_app')
    """, (norm_n, norm_p))
    conn.commit()

    cand_id = cursor.lastrowid
    new_cand = conn.execute("SELECT * FROM candidates WHERE id = ?", (cand_id,)).fetchone()
    conn.close()
    return dict(new_cand)

def check_duplicate_audio_hash(file_hash):
    """Checks if an audio submission with identical SHA-256 hash already exists."""
    if not file_hash:
        return None
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM audio_submissions WHERE file_hash = ?", (file_hash,)).fetchone()
    conn.close()
    return dict(row) if row else None

def save_audio_submission(candidate_id, submitter_name, phone_number, file_name, file_path, meta):
    """Saves audio submission record into Task 1 database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audio_submissions (
            candidate_id, submitter_name, phone_number, file_name, file_path, file_hash, file_size_bytes,
            duration_seconds, sample_rate_khz, bitrate_kbps, bitrate_is_derived, loudness_db, noise_quality_estimate, snr_db, quality_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_id,
        cu.norm_name(submitter_name),
        cu.norm_phone(phone_number),
        file_name,
        file_path,
        meta.get("file_hash", ""),
        meta.get("file_size_bytes", 0),
        meta.get("duration_seconds", 0.0),
        meta.get("sample_rate_khz", 0.0),
        meta.get("bitrate_kbps", 0.0),
        meta.get("bitrate_is_derived", 0),
        meta.get("loudness_db", 0.0),
        meta.get("noise_quality_estimate", ""),
        meta.get("snr_db", 0.0),
        meta.get("quality_score", 80)
    ))
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id

def get_all_audio_submissions():
    """Retrieves all audio submissions with joined candidate database metadata."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT 
            s.id,
            s.candidate_id,
            s.submitter_name,
            s.phone_number,
            s.file_name,
            s.file_path,
            s.file_hash,
            s.file_size_bytes,
            s.duration_seconds,
            s.sample_rate_khz,
            s.bitrate_kbps,
            s.bitrate_is_derived,
            s.loudness_db,
            s.noise_quality_estimate,
            s.snr_db,
            s.quality_score,
            s.submitted_at,
            c.email as candidate_email,
            c.city as candidate_city,
            c.skills as candidate_skills,
            c.sources_found as candidate_sources
        FROM audio_submissions s
        LEFT JOIN candidates c ON s.candidate_id = c.id
        ORDER BY s.submitted_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def log_field_conflict(candidate_id, field_name, source1_val, source2_val, chosen_val, resolution_method):
    """Logs data field conflicts when sources disagree (e.g. CTC vs Gig rate)."""
    conn = get_db_connection()
    conn.execute("""
        INSERT INTO field_conflicts (candidate_id, field_name, source1_val, source2_val, chosen_val, resolution_method)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (candidate_id, field_name, str(source1_val), str(source2_val), str(chosen_val), resolution_method))
    conn.commit()
    conn.close()

def check_duplicate_candidate(phone, email=""):
    """Used by Task 2 n8n duplicate alert workflow."""
    conn = get_db_connection()
    norm_p = cu.norm_phone(phone)
    norm_e = cu.norm_email(email)

    match = None
    if norm_e:
        match = conn.execute("SELECT * FROM candidates WHERE email = ? OR alt_email = ?", (norm_e, norm_e)).fetchone()
    if not match and norm_p:
        match = conn.execute("SELECT * FROM candidates WHERE phone = ?", (norm_p,)).fetchone()

    conn.close()
    return dict(match) if match else None

def update_candidate_skill_category(cand_id, category, event_type="llm_skill_tagging"):
    """Used by Task 2 n8n flow to write back auto-tagged skill category."""
    conn = get_db_connection()
    conn.execute("UPDATE candidates SET skill_category = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (category, cand_id))
    conn.execute("""
        INSERT INTO automation_logs (candidate_id, event_type, skill_category, payload)
        VALUES (?, ?, ?, ?)
    """, (cand_id, event_type, category, f'{{"skill_category": "{category}"}}'))
    conn.commit()
    conn.close()

def get_all_candidates():
    """Retrieves all candidate records from database."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM candidates ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
