"""
HelixRx Multi-Role Clinical & Patient Database Engine
Handles user authentication, role-based historical partitions (3-month for patients, 
6-month for clinicians), and comprehensive administrator audit analytics.
"""

import sqlite3
import hashlib
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "helixrx.db")


def hash_password(password: str) -> str:
    """Returns SHA-256 hash of plain-text password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables for accounts, patient sessions, and clinician sessions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Accounts Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Patient Screenings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            condition TEXT NOT NULL,
            vitals_json TEXT,
            medications_json TEXT,
            clinical_status TEXT,
            scanned_flag INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # 3. Clinician PGx Screenings Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinician_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinician_id INTEGER NOT NULL,
            patient_identifier TEXT NOT NULL,
            drugs_evaluated TEXT NOT NULL,
            egfr_val REAL,
            alt_val REAL,
            vcf_source TEXT,
            risk_summary TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clinician_id) REFERENCES users (id)
        )
    """)

    # Pre-seed Default Baseline Credentials
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, full_name, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            ("admin", "System Administrator", "9999999999", hash_password("admin123"), "Admin")
        )
        cursor.execute(
            "INSERT INTO users (username, full_name, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            ("doctor@helix.org", "Dr. Rajesh Rao (MD)", "9123456780", hash_password("doctor123"), "Clinician")
        )
        cursor.execute(
            "INSERT INTO users (username, full_name, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            ("patient@gmail.com", "Vinay Kumar", "9876543210", hash_password("patient123"), "Patient")
        )

    conn.commit()
    conn.close()


def register_user(username: str, full_name: str, phone: str, password: str, role: str = "Patient") -> dict:
    """Registers a new patient or clinician account."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, full_name, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
            (username.strip().lower(), full_name.strip(), phone.strip(), hash_password(password), role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        conn.close()
        return {"success": False, "error": "This username or email is already registered."}
    except Exception as e:
        conn.close()
        return {"success": False, "error": str(e)}


def authenticate_user(username: str, password: str) -> dict:
    """Validates login credentials against stored hashes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, full_name, phone, role, password_hash FROM users WHERE username = ?",
        (username.strip().lower(),)
    )
    user = cursor.fetchone()
    conn.close()

    if user and user["password_hash"] == hash_password(password):
        return {
            "authenticated": True,
            "user_id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "phone": user["phone"],
            "role": user["role"]
        }
    return {"authenticated": False}


# -------------------------------------------------------------
# PATIENT DATA HELPERS (3 MONTHS)
# -------------------------------------------------------------
def save_patient_evaluation(user_id: int, condition: str, vitals: dict, batch_evaluations: list, scanned: bool = False) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()

    overall_status = "Optimal"
    for r in batch_evaluations:
        if "Renal" in r.get("status", "") or "Contraindicated" in r.get("status", ""):
            overall_status = "Contraindicated"
            break
        elif not r.get("dose_correct", True):
            overall_status = "Adjustment Recommended"

    cursor.execute("""
        INSERT INTO patient_evaluations (
            user_id, condition, vitals_json, medications_json, clinical_status, scanned_flag, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        condition,
        json.dumps(vitals),
        json.dumps(batch_evaluations),
        overall_status,
        1 if scanned else 0,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_patient_history_3_months(user_id: int) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d 00:00:00")

    cursor.execute("""
        SELECT id, condition, vitals_json, medications_json, clinical_status, scanned_flag, timestamp
        FROM patient_evaluations
        WHERE user_id = ? AND timestamp >= ?
        ORDER BY timestamp DESC
    """, (user_id, cutoff))

    rows = cursor.fetchall()
    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "condition": r["condition"],
            "vitals": json.loads(r["vitals_json"]) if r["vitals_json"] else {},
            "medications": json.loads(r["medications_json"]) if r["medications_json"] else [],
            "clinical_status": r["clinical_status"],
            "scanned": bool(r["scanned_flag"]),
            "timestamp": r["timestamp"]
        })
    conn.close()
    return history


# -------------------------------------------------------------
# CLINICIAN DATA HELPERS (6 MONTHS)
# -------------------------------------------------------------
def save_clinician_evaluation(clinician_id: int, patient_id: str, drugs: list, egfr: float, alt: float, vcf: str, risk_summary: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO clinician_evaluations (
            clinician_id, patient_identifier, drugs_evaluated, egfr_val, alt_val, vcf_source, risk_summary, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clinician_id,
        patient_id or "Patient-Anonymous",
        ", ".join(drugs),
        egfr,
        alt,
        vcf,
        risk_summary,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_clinician_history_6_months(clinician_id: int) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d 00:00:00")

    cursor.execute("""
        SELECT id, patient_identifier, drugs_evaluated, egfr_val, alt_val, vcf_source, risk_summary, timestamp
        FROM clinician_evaluations
        WHERE clinician_id = ? AND timestamp >= ?
        ORDER BY timestamp DESC
    """, (clinician_id, cutoff))

    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# -------------------------------------------------------------
# ADMIN AUDIT & USAGE ANALYTICS HELPERS
# -------------------------------------------------------------
def get_admin_metrics() -> dict:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Patient'")
    total_patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'Clinician'")
    total_clinicians = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM patient_evaluations")
    patient_tests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clinician_evaluations")
    clinician_tests = cursor.fetchone()[0]

    cursor.execute("SELECT id, username, full_name, phone, role, created_at FROM users ORDER BY id DESC")
    all_users = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT p.id, u.full_name as patient_name, u.username, p.condition, p.clinical_status, p.scanned_flag, p.timestamp
        FROM patient_evaluations p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.timestamp DESC
    """)
    all_patient_records = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT c.id, u.full_name as clinician_name, c.patient_identifier, c.drugs_evaluated, c.egfr_val, c.alt_val, c.risk_summary, c.timestamp
        FROM clinician_evaluations c
        JOIN users u ON c.clinician_id = u.id
        ORDER BY c.timestamp DESC
    """)
    all_clinician_records = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_clinicians": total_clinicians,
        "total_evaluations": patient_tests + clinician_tests,
        "users": all_users,
        "patient_records": all_patient_records,
        "clinician_records": all_clinician_records
    }