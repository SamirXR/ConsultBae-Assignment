# Task 5 — Stretch Goal: 5,000 Gig Worker Audio Launch Post-Mortem

**Scenario**: We launch the audio collection web app to **5,000 gig workers over a single weekend**.

---

## 1. What Breaks First? (Bottlenecks & Failure Modes)

### A. Server I/O & Thread Pool Exhaustion (Python Single-Node Server)
- **Problem**: Serving audio uploads directly on a single synchronous or threaded Python process will saturate open socket descriptors and thread pools when hundreds of gig workers submit concurrently.
- **Impact**: HTTP 504 Gateway Timeouts, dropped connections, incomplete audio uploads.

### B. Disk I/O & Local Storage Exhaustion
- **Problem**: 5,000 workers submitting 1-minute audio recordings (~10MB WAV or ~1.5MB WebM each) will generate **7.5 GB to 50 GB** of raw audio files.
- **Impact**: Filling local disk space, leading to server crashes and database write locks.

### C. Synchronous Subprocess Metadata Extraction (`ffprobe`/`ffmpeg`)
- **Problem**: Running `ffmpeg volumedetect` synchronously inside the HTTP POST request thread consumes heavy CPU cycles per upload.
- **Impact**: CPU utilization spikes to 100%, queueing incoming requests and causing request timeouts (>30 seconds).

### D. Database Write Contention & Lock Errors (SQLite)
- **Problem**: SQLite uses database-level write locks. Concurrent writes from 5,000 workers attempting `INSERT INTO audio_submissions` will trigger `sqlite3.OperationalError: database is locked`.

### E. Duplicate Race Conditions
- **Problem**: Workers re-submitting forms rapidly on spotty mobile networks will create duplicate candidate and audio records due to uncoordinated write attempts.

---

## 2. Architectural Changes Needed Before Launch

```
[5,000 Mobile Gig Workers]
         │ (HTTPS Upload)
         ▼
 [Cloudflare / AWS CloudFront CDN]  <-- DDOS Protection & Rate Limiting
         │
         ▼
  [Load Balancer / Nginx]
         │
 ┌───────┴───────┐
 ▼               ▼
[API Node 1]   [API Node 2]         <-- Stateless FastAPI / Node App Nodes
 │               │
 ├───────────────┴──> Presigned Upload URL --> [AWS S3 / Cloudflare R2 Bucket]
 │                                              (Direct Audio File Upload)
 │
 ▼
[Redis Queue / Celery / BullMQ]     <-- Async Background Audio Processor
 │
 ├─> Worker 1: Run ffprobe/ffmpeg metadata extraction (duration, sample rate, loudness)
 ├─> Worker 2: Write metadata & link candidate record into PostgreSQL / MySQL
 └─> Worker 3: Trigger Task 2 n8n webhook for duplicate alert & LLM skill tagging
```

### Key Architectural Fixes:
1. **Direct-to-S3 / R2 Presigned Uploads**:
   - The browser requests a temporary presigned POST URL from the API, then uploads audio **directly to Object Storage (AWS S3 or Cloudflare R2)**.
   - Eliminates backend server bandwidth bottlenecks completely.

2. **Asynchronous Worker Queue (Celery / Redis)**:
   - Move `ffprobe`/`ffmpeg` metadata extraction out of the HTTP request lifecycle into background task queues.
   - The user gets an instant `< 200ms` HTTP response confirmation.

3. **Migrate SQLite to Managed Relational Database (PostgreSQL / AWS Aurora)**:
   - Replaces file-level locking with row-level locking, connection pooling (PgBouncer), and high write throughput.

4. **Idempotency Keys & Unique Constraints**:
   - Add DB unique constraint on `(phone_number, submission_hash)` or `(candidate_id, file_hash)` to prevent double submissions.

5. **Audio Transcoding & Compression on Frontend**:
   - Record in browser using low-bitrate compressed formats (`Opus / WebM` at 32 kbps) instead of uncompressed PCM WAV. Reduces payload size from 10MB to ~300KB per minute.

---

## 3. Cost & Infrastructure Estimate

| Component | Architecture | Estimated Weekend Cost (5,000 Users) |
| :--- | :--- | :--- |
| **Object Storage** | AWS S3 / Cloudflare R2 (~10GB Audio) | $0.15 - $0.30 |
| **Database** | Managed PostgreSQL (AWS RDS db.t4g.small) | $5.00 |
| **API Compute** | 2x Render / Railway App Nodes | $3.00 |
| **CDN / Protection** | Cloudflare Free Tier | $0.00 |
| **Total Cost** | **Scalable Cloud Architecture** | **< $10.00** |
