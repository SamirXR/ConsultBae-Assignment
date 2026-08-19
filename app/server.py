"""
ConsultBae Audio Collection App — Flask Server (Task 3)

Production-grade web server for audio submission, metadata extraction,
and candidate database integration. Uses Flask for routing and serves
a glassmorphism single-page application frontend.

Routes:
  GET  /                          → Main SPA (index.html)
  GET  /api/submissions           → List all audio submissions (JSON)
  POST /api/submissions           → Upload audio + extract properties
  GET  /api/export/candidates.csv → Download merged candidates CSV
  GET  /api/export/submissions.csv→ Download audio submissions CSV
  POST /api/check-duplicate       → Task 2 n8n duplicate check endpoint
  POST /api/candidates/update-skill → Task 2 n8n skill category write-back
  POST /api/automation-alert      → Task 2 n8n automation alert log
"""

import os
import sys
import csv
import io
import json

from flask import Flask, request, jsonify, send_from_directory, Response

# Add service and pipeline paths
sys.path.append(os.path.join(os.path.dirname(__file__), "services"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "pipeline"))

import db_service as db
import audio_processor as ap

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__,
            static_folder="static",
            static_url_path="/static")

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads", "audio")
os.makedirs(UPLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Task 3 — Main Web UI
# ---------------------------------------------------------------------------
@app.route("/")
@app.route("/index.html")
def index():
    """Serve the main single-page audio collection application."""
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------------------
# Task 3 — Audio Submissions API
# ---------------------------------------------------------------------------
@app.route("/api/submissions", methods=["GET"])
def list_submissions():
    """Return all audio submissions as JSON."""
    submissions = db.get_all_audio_submissions()
    return jsonify(submissions)


@app.route("/api/submissions", methods=["POST"])
def create_submission():
    """Handle audio file upload, extract metadata, and save to database."""
    submitter_name = request.form.get("submitter_name", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    audio_file = request.files.get("audio_file")

    if not submitter_name or not phone_number or not audio_file:
        return jsonify({
            "status": "error",
            "message": "Missing required fields (submitter_name, phone_number, or audio_file)"
        }), 400

    # Save uploaded file to disk
    orig_filename = audio_file.filename or "recording.webm"
    file_ext = os.path.splitext(orig_filename)[1] or ".webm"
    clean_filename = f"audio_{os.urandom(6).hex()}{file_ext}"
    save_path = os.path.join(UPLOADS_DIR, clean_filename)
    audio_file.save(save_path)

    # Extract audio properties using ffprobe/ffmpeg
    meta = ap.extract_audio_metadata(save_path)

    # SHA-256 duplicate audio check
    existing_audio = db.check_duplicate_audio_hash(meta["file_hash"])
    if existing_audio:
        os.remove(save_path)  # Cleanup duplicate file on disk
        return jsonify({
            "status": "duplicate_audio",
            "message": "Duplicate audio file detected (identical SHA-256 checksum)",
            "existing_submission": existing_audio,
            "metadata": meta
        })

    # Link or create candidate in Task 1 database
    cand = db.find_or_create_candidate(submitter_name, phone_number)

    # Save audio submission record
    web_audio_path = f"/uploads/audio/{clean_filename}"
    sub_id = db.save_audio_submission(
        candidate_id=cand["id"],
        submitter_name=submitter_name,
        phone_number=phone_number,
        file_name=clean_filename,
        file_path=web_audio_path,
        meta=meta
    )

    return jsonify({
        "status": "success",
        "submission_id": sub_id,
        "candidate": cand,
        "metadata": meta,
        "file_url": web_audio_path
    })


# ---------------------------------------------------------------------------
# Serve Uploaded Audio Files
# ---------------------------------------------------------------------------
@app.route("/uploads/audio/<path:filename>")
def serve_audio(filename):
    """Serve uploaded audio files for playback in the browser."""
    return send_from_directory(os.path.abspath(UPLOADS_DIR), filename)


# ---------------------------------------------------------------------------
# CSV Export Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/export/candidates.csv")
def export_candidates_csv():
    """Export merged master candidates as downloadable CSV."""
    candidates = db.get_all_candidates()
    if not candidates:
        return jsonify({"error": "No candidates found"}), 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(candidates[0].keys()))
    writer.writeheader()
    writer.writerows(candidates)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=consultbae_merged_candidates.csv"}
    )


@app.route("/api/export/submissions.csv")
def export_submissions_csv():
    """Export audio submissions as downloadable CSV."""
    submissions = db.get_all_audio_submissions()
    if not submissions:
        return jsonify({"error": "No submissions found"}), 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(submissions[0].keys()))
    writer.writeheader()
    writer.writerows(submissions)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=consultbae_audio_submissions.csv"}
    )


# ---------------------------------------------------------------------------
# Task 2 — n8n Automation Integration Endpoints
# ---------------------------------------------------------------------------
@app.route("/api/check-duplicate", methods=["POST"])
def check_duplicate():
    """Check if a candidate already exists in the database (for n8n workflow)."""
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "")
    email_val = data.get("email", "")

    match = db.check_duplicate_candidate(phone, email_val)
    return jsonify({
        "is_duplicate": bool(match),
        "matched_candidate": match
    })


@app.route("/api/candidates/update-skill", methods=["POST"])
def update_skill():
    """Write-back skill category from n8n LLM classification step."""
    data = request.get_json(silent=True) or {}
    cand_id = data.get("candidate_id")
    category = data.get("skill_category", "general-tech")

    if not cand_id:
        return jsonify({"status": "error", "message": "Missing candidate_id"}), 400

    db.update_candidate_skill_category(cand_id, category)
    return jsonify({
        "status": "success",
        "candidate_id": cand_id,
        "updated_skill_category": category
    })


@app.route("/api/automation-alert", methods=["POST"])
def automation_alert():
    """Receive and log automation alerts from n8n workflow."""
    data = request.get_json(silent=True) or {}
    print(f"[n8n] automation alert: {json.dumps(data)}")
    return jsonify({"status": "alert_received", "payload": data})


# ---------------------------------------------------------------------------
# Run Server
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[server] ConsultBae Audio Collection App listening on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
