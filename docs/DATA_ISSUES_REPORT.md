# Task 4 — Data Quality Issues Report

This report details every data quality problem identified across the 3 raw source CSV files (`source1_naukri_applicants.csv`, `source2_gig_workers.csv`, and `source3_cbnexus_contacts.csv`), along with the specific normalization logic applied during ingestion.

---

## Summary of Planted Data Issues Caught

| Issue ID | File / Source | Specific Location / Row | Description of Data Anomaly | Resolution / Action Taken |
| :--- | :--- | :--- | :--- | :--- |
| **ISSUE-01** | `source2_gig_workers.csv` | Row 19 (Line 20) | **Shifted Columns Bug**: Skill tags (`"react, javascript, mysql"`) pushed into `email_id` position, shifting Email to `worker_name` and Name to `rate`. | Implemented structural check in `ingest.py`. Detects `@` in column 1 to re-align columns before parsing. |
| **ISSUE-02** | `source2_gig_workers.csv` | Row 11 (Line 12) | **Empty / Blank Row**: Row containing all empty strings `['', '', '', '', '', '']`. | Added filter `if not any(row): continue` during ingestion. |
| **ISSUE-03** | `source3_cbnexus_contacts.csv` | Line 16 | **Embedded Duplicate Header**: Repeated CSV header line `Name,Phone Number,City...` inside data rows. | Added header check `if row[0] == "Name": continue` during row iteration. |
| **ISSUE-04** | `source1_naukri_applicants.csv` | Various (e.g. Row 2 vs Row 5) | **CTC Currency/Format Inconsistency**: Some CTCs are in absolute INR (`417964`), while others are float Lakhs Per Annum (`4.2`). | Standardized in `clean_utils.norm_ctc`: values > 1000 converted by `val / 100000.0` (e.g. `417964` -> `4.18 LPA`). |
| **ISSUE-05** | `source1_naukri_applicants.csv` | Rows 25 vs 31 | **Abbreviated Name & Duplicate Entry**: Row 25 (`R. Verma`, `rohit.verma13@...`) vs Row 31 (`Rohit Verma`, `rohit.verma13@...`). | Merged via Email/Phone graph. Selection logic chooses longest unabbreviated title-cased name (`"Rohit Verma"`). |
| **ISSUE-06** | `source1_naukri_applicants.csv` | Various | **Heterogeneous Date Formats**: Dates in `DD-MM-YYYY`, `YYYY-MM-DD`, `MM/DD/YYYY`, and `D MMM YYYY` (e.g. `7 Jul 2026`). | Parsed using multi-format strptime list in `clean_utils.norm_date` into ISO standard `YYYY-MM-DD`. |
| **ISSUE-07** | All 3 Sources | Various | **Inconsistent Phone Formats**: Numbers formatted with `+91-`, leading `0`, `91` prefix, hyphens, and spaces. | Normalized via regex `clean_utils.norm_phone` to standard 10-digit national string (e.g. `9000000254`). |
| **ISSUE-08** | All 3 Sources | Various | **City Name Variations & Trailing Spaces**: `GURGAON`, `gurugram `, `Noida `, `PUNE`, `Delhi NCR`, `new delhi`, `bangalore`. | Standardized via dictionary lookup in `clean_utils.norm_city` into canonical names (`Gurugram`, `Delhi`, `Bengaluru`, `Noida`, `Pune`). |
| **ISSUE-09** | `source2_gig_workers.csv` | Various | **Uppercase Email Addresses**: `ISHA.CHOPRA95@MAILTEST...`, `DEEPAK.NAIR44@EXAMPLE.COM`. | Lowercased and whitespace-trimmed via `clean_utils.norm_email`. |
| **ISSUE-10** | `source2_gig_workers.csv` | Various | **Heterogeneous Gig Rates**: Rates mixed between hourly (`1415/hr`) and monthly (`72k/month`, `15k/month`). | Parsed numeric value and period unit separately (`gig_rate_num`, `gig_rate_unit`) for query capability. |
| **ISSUE-11** | `source3_cbnexus_contacts.csv` | Various | **Heterogeneous Verification Booleans**: Values represented as `Y`, `yes`, `Yes`, `No`, `N`. | Converted to integer `1` (Verified) and `0` (Unverified) via `clean_utils.norm_verified`. |
| **ISSUE-12** | Across Sources | Various | **Same Name, Different Individuals**: Two separate candidates named `Arjun Mehta` (one with phone `9000000131`, one with phone `9000000272`). | Multi-tier identity resolution prevents incorrect merging by enforcing Phone/Email boundary checks. |

---

## Final Ingestion Breakdown
- **Total Raw Records Processed**: 103
- **Total Deduplicated Candidates Ingested**: 55
- **SQLite Database File**: `database/consultbae.db`
