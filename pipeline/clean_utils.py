import re
from datetime import datetime

def norm_phone(p):
    """
    Normalizes Indian phone numbers into a standard 10-digit string.
    Handles +91-, 91 prefix, 0 prefix, spaces, and hyphens.
    """
    if not p:
        return ""
    digits = re.sub(r"\D", "", str(p))
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 10:
        return digits
    return digits

def norm_email(e):
    """Normalizes email address to lowercase stripped format."""
    if not e:
        return ""
    return str(e).strip().lower()

def norm_name(n):
    """Normalizes candidate name to clean Title Case."""
    if not n:
        return ""
    n = str(n).strip()
    # Normalize initials e.g. R. Verma -> R. Verma
    words = n.split()
    clean_words = []
    for w in words:
        if len(w) == 1 or (len(w) == 2 and w.endswith(".")):
            clean_words.append(w.upper())
        else:
            clean_words.append(w.capitalize())
    return " ".join(clean_words)

def norm_city(c):
    """Standardizes city names across heterogeneous inputs."""
    if not c:
        return ""
    c = str(c).strip().title()
    mapping = {
        "Gurgaon": "Gurugram",
        "Gurugram": "Gurugram",
        "Delhi Ncr": "Delhi",
        "New Delhi": "Delhi",
        "Delhi": "Delhi",
        "Bangalore": "Bengaluru",
        "Bengaluru": "Bengaluru",
        "Noida": "Noida",
        "Pune": "Pune"
    }
    return mapping.get(c, c)

def norm_ctc(ctc_val):
    """
    Normalizes CTC format inconsistency in Source 1:
    - Absolute INR e.g. 417964 -> 4.18 LPA
    - LPA Float e.g. 4.2 -> 4.2 LPA
    """
    if not ctc_val:
        return None
    try:
        val = float(str(ctc_val).strip())
        if val > 1000:
            # Absolute INR -> convert to Lakhs (LPA)
            return round(val / 100000.0, 2)
        return round(val, 2)
    except ValueError:
        return None

def norm_date(date_str):
    """
    Parses heterogeneous date formats in Source 1 into YYYY-MM-DD.
    Formats handled:
    - DD-MM-YYYY (e.g. 24-07-2026)
    - YYYY-MM-DD (e.g. 2026-08-08)
    - MM/DD/YYYY (e.g. 07/13/2026)
    - D MMM YYYY (e.g. 7 Jul 2026, 15 Jul 2026)
    """
    if not date_str:
        return ""
    date_str = str(date_str).strip()
    
    formats = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d %b %Y",
        "%b %d, %Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str

def norm_rate(rate_str):
    """
    Parses rate strings like '1415/hr' or '15k/month' or '72k/month'.
    Returns tuple: (numeric_rate, period_unit)
    """
    if not rate_str:
        return None, ""
    rate_str = str(rate_str).strip().lower()
    
    # Check monthly 'k' pattern e.g. 15k/month
    m_k = re.search(r"(\d+(?:\.\d+)?)\s*k\s*/\s*(month|hr)", rate_str)
    if m_k:
        num = float(m_k.group(1)) * 1000
        unit = m_k.group(2)
        return num, unit
    
    m_num = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(month|hr)", rate_str)
    if m_num:
        num = float(m_num.group(1))
        unit = m_num.group(2)
        return num, unit
        
    return None, rate_str

def norm_status(status_str):
    """Normalizes gig status (Active, Inactive, Paused)."""
    if not status_str:
        return "Active"
    s = str(status_str).strip().capitalize()
    if s in ["Active", "Inactive", "Paused"]:
        return s
    return "Active"

def norm_verified(v_str):
    """Normalizes verification column (Y/Yes/1 -> 1, N/No/0 -> 0)."""
    if not v_str:
        return 0
    v = str(v_str).strip().lower()
    if v in ["y", "yes", "1", "true"]:
        return 1
    return 0

def norm_skills(skills_list):
    """
    Merges multiple skill strings, deduplicating case-insensitively.
    Returns clean comma-separated skill string.
    """
    skill_set = set()
    skill_order = []
    
    for s_item in skills_list:
        if not s_item:
            continue
        parts = [p.strip() for p in str(s_item).split(",")]
        for p in parts:
            if not p:
                continue
            p_key = p.lower()
            if p_key not in skill_set:
                skill_set.add(p_key)
                skill_order.append(p)
                
    return ", ".join(skill_order)
