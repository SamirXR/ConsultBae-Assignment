import os
import csv
import sqlite3
import argparse
from collections import defaultdict
import clean_utils as cu

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "consultbae.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")

def init_db(db_path, schema_path):
    """Initializes SQLite database schema."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    return conn

def get_source_file_path(base_dir, filename):
    """Checks data/raw/ directory first, falling back to root base_dir."""
    raw_path = os.path.join(base_dir, "data", "raw", filename)
    if os.path.exists(raw_path):
        return raw_path
    return os.path.join(base_dir, filename)

def parse_and_load_raw_data(conn, base_dir):
    """Parses raw CSV files, handles structural bugs, and logs data issues."""
    raw_records = []
    data_issues_log = []

    # 1. Source 1: Naukri Applicants
    s1_path = get_source_file_path(base_dir, "source1_naukri_applicants.csv")
    with open(s1_path, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for idx, row in enumerate(r):
            if not row or not row.get("Full Name"):
                data_issues_log.append({
                    "source_file": "source1_naukri_applicants.csv",
                    "row_num": idx + 2,
                    "issue_type": "EMPTY_ROW",
                    "description": "Skipped blank or empty applicant row",
                    "severity": "LOW",
                    "action_taken": "SKIPPED"
                })
                continue
            
            raw_ctc = row.get("Current CTC", "")
            norm_ctc_val = cu.norm_ctc(raw_ctc)
            if raw_ctc and (str(raw_ctc).isdigit() or "LPA" not in str(raw_ctc).upper()):
                data_issues_log.append({
                    "source_file": "source1_naukri_applicants.csv",
                    "row_num": idx + 2,
                    "issue_type": "CTC_FORMAT_VARIATION",
                    "description": f"Raw CTC value '{raw_ctc}' converted to {norm_ctc_val} LPA",
                    "severity": "MEDIUM",
                    "action_taken": "NORMALIZED_TO_LPA"
                })

            # Store raw in SQLite
            conn.execute("""
                INSERT INTO raw_naukri_applicants (full_name, email, phone, city, experience, ctc, applied_date, skills)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (row.get("Full Name"), row.get("Email"), row.get("Phone"), row.get("City"),
                  row.get("Experience (Years)"), row.get("Current CTC"), row.get("Applied Date"), row.get("Skills")))
            
            raw_records.append({
                "source_id": f"s1_{idx}",
                "source": "naukri",
                "name": cu.norm_name(row.get("Full Name")),
                "email": cu.norm_email(row.get("Email")),
                "phone": cu.norm_phone(row.get("Phone")),
                "city": cu.norm_city(row.get("City")),
                "exp": row.get("Experience (Years)"),
                "ctc": norm_ctc_val,
                "applied_date": cu.norm_date(row.get("Applied Date")),
                "skills": row.get("Skills"),
                "gig_rate": "",
                "gig_status": "",
                "cbnexus_verified": 0,
                "cbnexus_projects": 0
            })

    # 2. Source 2: Gig Workers (Handles blank rows & column shift anomaly)
    s2_path = get_source_file_path(base_dir, "source2_gig_workers.csv")
    with open(s2_path, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        for idx, row in enumerate(r):
            row_num = idx + 2
            if not any(row):  # Blank row 11
                data_issues_log.append({
                    "source_file": "source2_gig_workers.csv",
                    "row_num": row_num,
                    "issue_type": "BLANK_ROW",
                    "description": "Entirely empty row encountered",
                    "severity": "LOW",
                    "action_taken": "SKIPPED"
                })
                continue
            
            # Check for column shift bug (e.g. Row 19 where skills are in col 0 and email in col 1)
            if len(row) >= 6 and "@" in row[1]:
                data_issues_log.append({
                    "source_file": "source2_gig_workers.csv",
                    "row_num": row_num,
                    "issue_type": "SHIFTED_COLUMNS_BUG",
                    "description": f"Skill tags '{row[0]}' in email column; shifted email '{row[1]}' and name '{row[2]}'",
                    "severity": "HIGH",
                    "action_taken": "REALIGNED_COLUMNS"
                })
                skills = row[0]
                email = cu.norm_email(row[1])
                name = cu.norm_name(row[2])
                rate = row[3]
                loc = cu.norm_city(row[4])
                status = cu.norm_status(row[5])
            else:
                email = cu.norm_email(row[0])
                name = cu.norm_name(row[1])
                rate = row[2] if len(row) > 2 else ""
                loc = cu.norm_city(row[3]) if len(row) > 3 else ""
                status = cu.norm_status(row[4]) if len(row) > 4 else ""
                skills = row[5] if len(row) > 5 else ""

            conn.execute("""
                INSERT INTO raw_gig_workers (email_id, worker_name, rate, location, status, skill_tags)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email, name, rate, loc, status, skills))

            raw_records.append({
                "source_id": f"s2_{idx}",
                "source": "gig",
                "name": name,
                "email": email,
                "phone": "",
                "city": loc,
                "exp": None,
                "ctc": None,
                "applied_date": "",
                "skills": skills,
                "gig_rate": rate,
                "gig_status": status,
                "cbnexus_verified": 0,
                "cbnexus_projects": 0
            })

    # 3. Source 3: CBNexus Contacts (Handles embedded repeated header)
    s3_path = get_source_file_path(base_dir, "source3_cbnexus_contacts.csv")
    with open(s3_path, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        for idx, row in enumerate(r):
            row_num = idx + 2
            if not any(row):
                continue
            if row[0] == "Name":  # Embedded repeated header line 16
                data_issues_log.append({
                    "source_file": "source3_cbnexus_contacts.csv",
                    "row_num": row_num,
                    "issue_type": "REPEATED_HEADER_ROW",
                    "description": "Mid-file duplicate header row encountered",
                    "severity": "MEDIUM",
                    "action_taken": "SKIPPED"
                })
                continue

            name = cu.norm_name(row[0])
            phone = cu.norm_phone(row[1])
            city = cu.norm_city(row[2])
            verified = cu.norm_verified(row[3])
            try:
                projects = int(row[4])
            except ValueError:
                projects = 0

            conn.execute("""
                INSERT INTO raw_cbnexus_contacts (name, phone_number, city, verified, projects_completed)
                VALUES (?, ?, ?, ?, ?)
            """, (row[0], row[1], row[2], row[3], row[4]))

            raw_records.append({
                "source_id": f"s3_{idx}",
                "source": "cbnexus",
                "name": name,
                "email": "",
                "phone": phone,
                "city": city,
                "exp": None,
                "ctc": None,
                "applied_date": "",
                "skills": "",
                "gig_rate": "",
                "gig_status": "",
                "cbnexus_verified": verified,
                "cbnexus_projects": projects
            })

    conn.commit()
    return raw_records, data_issues_log

def merge_and_deduplicate(raw_records):
    """
    Performs multi-tier entity resolution:
    - Tier 1: Union-Find graph matching by Email OR Phone.
    - Tier 2: Match unlinked records by (Name + City) composite key.
    """
    parent = {r["source_id"]: r["source_id"] for r in raw_records}
    review_flag_list = []

    def find(i):
        if parent[i] == i:
            return i
        parent[i] = find(parent[i])
        return parent[i]

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    # Tier 1: Index by Email and Phone
    email_map = defaultdict(list)
    phone_map = defaultdict(list)
    for r in raw_records:
        if r["email"]:
            email_map[r["email"]].append(r["source_id"])
        if r["phone"]:
            phone_map[r["phone"]].append(r["source_id"])

    for ids in email_map.values():
        for i in range(len(ids) - 1):
            union(ids[0], ids[i + 1])

    for ids in phone_map.values():
        for i in range(len(ids) - 1):
            union(ids[0], ids[i + 1])

    # Tier 2: Composite (Name + City) match
    name_city_map = defaultdict(list)
    for r in raw_records:
        name_city_map[(r["name"], r["city"])].append(r["source_id"])

    for (name, city), ids in name_city_map.items():
        groups = defaultdict(list)
        for id_val in ids:
            groups[find(id_val)].append(id_val)
        
        group_roots = list(groups.keys())
        if len(group_roots) > 1:
            for i in range(len(group_roots) - 1):
                root1, root2 = group_roots[i], group_roots[i + 1]
                e1 = {r["email"] for r in raw_records if find(r["source_id"]) == root1 and r["email"]}
                e2 = {r["email"] for r in raw_records if find(r["source_id"]) == root2 and r["email"]}
                p1 = {r["phone"] for r in raw_records if find(r["source_id"]) == root1 and r["phone"]}
                p2 = {r["phone"] for r in raw_records if find(r["source_id"]) == root2 and r["phone"]}

                # Check if merging root1 & root2 introduces conflicting email or phone
                if not (e1 and e2 and e1 != e2) and not (p1 and p2 and p1 != p2):
                    union(root1, root2)
                else:
                    review_flag_list.append({
                        "name": name,
                        "city": city,
                        "cluster_1_ids": ",".join([r["source_id"] for r in raw_records if find(r["source_id"]) == root1]),
                        "cluster_2_ids": ",".join([r["source_id"] for r in raw_records if find(r["source_id"]) == root2]),
                        "reason": "Matching Name & City but conflicting Phone/Email IDs (e.g. distinct candidates with same name)"
                    })

    # Group records into clusters
    clusters = defaultdict(list)
    for r in raw_records:
        clusters[find(r["source_id"])].append(r)

    merged_candidates = []
    for cid, recs in clusters.items():
        names = [r["name"] for r in recs if r["name"]]
        best_name = max(names, key=lambda n: len(n)) if names else ""

        emails = list(dict.fromkeys([r["email"] for r in recs if r["email"]]))
        primary_email = emails[0] if len(emails) > 0 else ""
        alt_email = emails[1] if len(emails) > 1 else ""

        phones = list(dict.fromkeys([r["phone"] for r in recs if r["phone"]]))
        primary_phone = phones[0] if len(phones) > 0 else ""

        cities = list(dict.fromkeys([r["city"] for r in recs if r["city"]]))
        primary_city = cities[0] if len(cities) > 0 else ""

        exp_list = [r["exp"] for r in recs if r["exp"] is not None and r["exp"] != ""]
        ctc_list = [r["ctc"] for r in recs if r["ctc"] is not None and r["ctc"] != ""]
        applied_dates = [r["applied_date"] for r in recs if r["applied_date"]]

        experience_years = float(exp_list[0]) if exp_list else None
        ctc_lpa = float(ctc_list[0]) if ctc_list else None
        applied_date = applied_dates[0] if applied_dates else ""

        rates = [r["gig_rate"] for r in recs if r["gig_rate"]]
        statuses = [r["gig_status"] for r in recs if r["gig_status"]]
        gig_rate = rates[0] if rates else ""
        gig_status = statuses[0] if statuses else ""

        num_rate, rate_unit = cu.norm_rate(gig_rate)

        verified_vals = [r["cbnexus_verified"] for r in recs if r["source"] == "cbnexus"]
        projects_vals = [r["cbnexus_projects"] for r in recs if r["source"] == "cbnexus"]

        cbnexus_verified = max(verified_vals) if verified_vals else 0
        cbnexus_projects = max(projects_vals) if projects_vals else 0

        all_skills_str = [r["skills"] for r in recs if r["skills"]]
        merged_skills = cu.norm_skills(all_skills_str)

        sources_found = ",".join(sorted(list(set(r["source"] for r in recs))))

        merged_candidates.append({
            "full_name": best_name,
            "email": primary_email,
            "alt_email": alt_email,
            "phone": primary_phone,
            "city": primary_city,
            "experience_years": experience_years,
            "ctc_lpa": ctc_lpa,
            "applied_date": applied_date,
            "gig_rate": gig_rate,
            "gig_rate_num": num_rate,
            "gig_rate_unit": rate_unit,
            "gig_status": gig_status,
            "skills": merged_skills,
            "cbnexus_verified": cbnexus_verified,
            "cbnexus_projects": cbnexus_projects,
            "sources_found": sources_found
        })

    return merged_candidates, review_flag_list

def export_csv_dict(data, output_path):
    """Exports list of dicts to CSV."""
    if not data:
        return
    headers = list(data[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def run_pipeline(base_dir):
    """Main ETL pipeline runner."""
    print("[pipeline] Running ConsultBae Task 1 Ingestion Pipeline...")
    conn = init_db(DB_PATH, SCHEMA_PATH)
    raw_records, data_issues_log = parse_and_load_raw_data(conn, base_dir)
    print(f"  [+] Loaded {len(raw_records)} raw records into lineage tables.")

    merged, review_flags = merge_and_deduplicate(raw_records)
    print(f"  [+] Entity Resolution complete: Merged into {len(merged)} unique candidate records.")

    for m in merged:
        conn.execute("""
            INSERT INTO candidates (
                full_name, email, alt_email, phone, city, experience_years, ctc_lpa, applied_date,
                gig_rate, gig_rate_num, gig_rate_unit, gig_status, skills, cbnexus_verified, cbnexus_projects, sources_found
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            m["full_name"], m["email"], m["alt_email"], m["phone"], m["city"],
            m["experience_years"], m["ctc_lpa"], m["applied_date"], m["gig_rate"],
            m["gig_rate_num"], m["gig_rate_unit"], m["gig_status"], m["skills"],
            m["cbnexus_verified"], m["cbnexus_projects"], m["sources_found"]
        ))

    conn.commit()
    conn.close()

    # Generate Export Files (writes to data/processed/)
    proc_dir = os.path.join(base_dir, "data", "processed")
    os.makedirs(proc_dir, exist_ok=True)

    export_csv_dict(merged, os.path.join(proc_dir, "consultbae_merged_candidates.csv"))
    export_csv_dict(data_issues_log, os.path.join(proc_dir, "data_issues_log.csv"))
    export_csv_dict(review_flags, os.path.join(proc_dir, "possible_duplicates_review.csv"))

    print(f"[ok] Ingested database saved to: {os.path.abspath(DB_PATH)}")
    print(f"  -> Master Candidates CSV: {os.path.abspath(os.path.join(proc_dir, 'consultbae_merged_candidates.csv'))}")
    print(f"  -> Data Issues Audit Log: {os.path.abspath(os.path.join(proc_dir, 'data_issues_log.csv'))}")
    print(f"  -> Possible Duplicates:   {os.path.abspath(os.path.join(proc_dir, 'possible_duplicates_review.csv'))}")
    print("[done]\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ConsultBae Data Pipeline")
    parser.add_argument("--dir", default=os.path.join(os.path.dirname(__file__), ".."), help="Directory containing CSV files")
    args = parser.parse_args()
    
    base_dir = os.path.abspath(args.dir)
    run_pipeline(base_dir)
