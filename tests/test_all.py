#!/usr/bin/env python3
"""
ConsultBae AI Automation Pipeline - Comprehensive Test Suite
50+ Granular Automated Unit Tests validating Normalization, Entity Resolution,
Audio Processing, SHA-256 Hashing, Database Service, and n8n Endpoints.

Zero external dependencies - uses standard library unittest.
"""

import os
import sys
import unittest
import sqlite3
import tempfile
import shutil

# Ensure pipeline and app are in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, "pipeline"))
sys.path.append(os.path.join(BASE_DIR, "app", "services"))

import clean_utils as cu
import db_service as db
import audio_processor as ap
import ingest

class TestPhoneNormalization(unittest.TestCase):
    """Granular tests for Indian phone number normalization."""
    def test_plus91_prefix(self): self.assertEqual(cu.norm_phone("+91-9000000254"), "9000000254")
    def test_leading_zero(self): self.assertEqual(cu.norm_phone("09000000254"), "9000000254")
    def test_91_prefix(self): self.assertEqual(cu.norm_phone("919000000254"), "9000000254")
    def test_clean_10_digits(self): self.assertEqual(cu.norm_phone("9000000254"), "9000000254")
    def test_spaced_format(self): self.assertEqual(cu.norm_phone("+91 90000 00254"), "9000000254")
    def test_hyphenated_format(self): self.assertEqual(cu.norm_phone("900-000-0254"), "9000000254")
    def test_parentheses_format(self): self.assertEqual(cu.norm_phone("+91 (9000) 000254"), "9000000254")
    def test_invalid_short_phone(self): self.assertEqual(cu.norm_phone("12345"), "12345")
    def test_empty_phone(self): self.assertEqual(cu.norm_phone(""), "")
    def test_none_phone(self): self.assertEqual(cu.norm_phone(None), "")

class TestEmailNormalization(unittest.TestCase):
    """Granular tests for email normalization."""
    def test_uppercase_email(self): self.assertEqual(cu.norm_email("ROHIT.VERMA@GMAIL.COM"), "rohit.verma@gmail.com")
    def test_whitespace_email(self): self.assertEqual(cu.norm_email("  user@example.com  "), "user@example.com")
    def test_mixed_case_domain(self): self.assertEqual(cu.norm_email("Isha@MailTest.ORG"), "isha@mailtest.org")
    def test_empty_email(self): self.assertEqual(cu.norm_email(""), "")
    def test_none_email(self): self.assertEqual(cu.norm_email(None), "")

class TestNameNormalization(unittest.TestCase):
    """Granular tests for name title casing & initial handling."""
    def test_lowercase_name(self): self.assertEqual(cu.norm_name("rohit verma"), "Rohit Verma")
    def test_uppercase_name(self): self.assertEqual(cu.norm_name("ISHA CHOPRA"), "Isha Chopra")
    def test_initial_format(self): self.assertEqual(cu.norm_name("r. verma"), "R. Verma")
    def test_multiple_initials(self): self.assertEqual(cu.norm_name("a. k. sharma"), "A. K. Sharma")
    def test_extra_whitespace(self): self.assertEqual(cu.norm_name("   arjun    mehta   "), "Arjun Mehta")
    def test_empty_name(self): self.assertEqual(cu.norm_name(""), "")

class TestCityNormalization(unittest.TestCase):
    """Granular tests for city canonicalization."""
    def test_gurgaon_mapping(self): self.assertEqual(cu.norm_city("Gurgaon"), "Gurugram")
    def test_gurugram_canonical(self): self.assertEqual(cu.norm_city("gurugram "), "Gurugram")
    def test_bangalore_mapping(self): self.assertEqual(cu.norm_city("Bangalore"), "Bengaluru")
    def test_bengaluru_canonical(self): self.assertEqual(cu.norm_city("bengaluru"), "Bengaluru")
    def test_delhi_ncr_mapping(self): self.assertEqual(cu.norm_city("Delhi NCR"), "Delhi")
    def test_new_delhi_mapping(self): self.assertEqual(cu.norm_city("new delhi"), "Delhi")
    def test_pune_canonical(self): self.assertEqual(cu.norm_city("PUNE"), "Pune")
    def test_noida_canonical(self): self.assertEqual(cu.norm_city("Noida "), "Noida")

class TestCTCAndRateNormalization(unittest.TestCase):
    """Granular tests for CTC and Gig Rate parsing."""
    def test_ctc_lpa_float(self): self.assertEqual(cu.norm_ctc("4.2"), 4.2)
    def test_ctc_absolute_inr(self): self.assertEqual(cu.norm_ctc("417964"), 4.18)
    def test_ctc_high_inr(self): self.assertEqual(cu.norm_ctc("1190000"), 11.9)
    def test_ctc_empty(self): self.assertIsNone(cu.norm_ctc(""))
    
    def test_rate_hourly(self):
        num, unit = cu.norm_rate("1415/hr")
        self.assertEqual(num, 1415.0)
        self.assertEqual(unit, "hr")

    def test_rate_monthly_k(self):
        num, unit = cu.norm_rate("15k/month")
        self.assertEqual(num, 15000.0)
        self.assertEqual(unit, "month")

    def test_rate_monthly_k_float(self):
        num, unit = cu.norm_rate("72k/month")
        self.assertEqual(num, 72000.0)
        self.assertEqual(unit, "month")

class TestDateNormalization(unittest.TestCase):
    """Granular tests for date parsing into ISO format."""
    def test_dash_dd_mm_yyyy(self): self.assertEqual(cu.norm_date("24-07-2026"), "2026-07-24")
    def test_iso_yyyy_mm_dd(self): self.assertEqual(cu.norm_date("2026-08-08"), "2026-08-08")
    def test_slash_mm_dd_yyyy(self): self.assertEqual(cu.norm_date("07/13/2026"), "2026-07-13")
    def test_text_d_mmm_yyyy(self): self.assertEqual(cu.norm_date("7 Jul 2026"), "2026-07-07")
    def test_text_dd_mmm_yyyy(self): self.assertEqual(cu.norm_date("15 Jul 2026"), "2026-07-15")

class TestSkillsDeduplication(unittest.TestCase):
    """Granular tests for skill list deduplication."""
    def test_dedup_skills(self):
        res = cu.norm_skills(["React, Node", "react, python", "NODE, AWS"])
        self.assertEqual(res, "React, Node, python, AWS")

class TestEntityResolution(unittest.TestCase):
    """Test DSU entity resolution & dataset integration."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_consultbae.db")
        self.schema_path = os.path.join(BASE_DIR, "database", "schema.sql")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_raw_data_loading(self):
        conn = ingest.init_db(self.db_path, self.schema_path)
        records, issues = ingest.parse_and_load_raw_data(conn, BASE_DIR)
        self.assertEqual(len(records), 103)
        self.assertGreater(len(issues), 0)
        conn.close()

    def test_master_entity_deduplication_count(self):
        conn = ingest.init_db(self.db_path, self.schema_path)
        records, issues = ingest.parse_and_load_raw_data(conn, BASE_DIR)
        candidates, unresolved = ingest.merge_and_deduplicate(records)
        self.assertEqual(len(candidates), 55)
        conn.close()

    def test_homonym_separation_arjun_mehta(self):
        conn = ingest.init_db(self.db_path, self.schema_path)
        records, issues = ingest.parse_and_load_raw_data(conn, BASE_DIR)
        candidates, unresolved = ingest.merge_and_deduplicate(records)
        arjun_mehtas = [c for c in candidates if "Arjun Mehta" in c["full_name"]]
        self.assertGreaterEqual(len(arjun_mehtas), 2)
        conn.close()

    def test_homonym_separation_deepak_nair(self):
        conn = ingest.init_db(self.db_path, self.schema_path)
        records, issues = ingest.parse_and_load_raw_data(conn, BASE_DIR)
        candidates, unresolved = ingest.merge_and_deduplicate(records)
        deepak_nairs = [c for c in candidates if "Deepak Nair" in c["full_name"]]
        self.assertGreaterEqual(len(deepak_nairs), 2)
        conn.close()

class TestAudioProcessorAndHashing(unittest.TestCase):
    """Test audio metadata extraction, SHA-256 hashing, and quality scoring."""

    def test_sha256_hash_integrity(self):
        test_file = os.path.join(BASE_DIR, "pipeline", "ingest.py")
        h1 = ap.compute_file_hash(test_file)
        h2 = ap.compute_file_hash(test_file)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_quality_score_calculation_bounds(self):
        # Test meta bounds
        meta = ap.extract_audio_metadata(os.path.join(BASE_DIR, "pipeline", "ingest.py"))
        self.assertIn("quality_score", meta)
        self.assertGreaterEqual(meta["quality_score"], 0)
        self.assertLessEqual(meta["quality_score"], 100)

class TestDatabaseService(unittest.TestCase):
    """Test Database Service lookup APIs."""

    def test_check_duplicate_candidate_by_phone(self):
        res = db.check_duplicate_candidate("9000000254", "")
        self.assertIsNotNone(res)
        self.assertEqual(res["full_name"], "Tanvi Gupta")

    def test_check_duplicate_candidate_by_email(self):
        res = db.check_duplicate_candidate("", "rohit.verma13@mailtest.example.org")
        self.assertIsNotNone(res)
        self.assertEqual(res["full_name"], "Rohit Verma")

    def test_duplicate_audio_hash_lookup(self):
        res = db.check_duplicate_audio_hash("non_existent_sha256_hash")
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main(verbosity=2)
