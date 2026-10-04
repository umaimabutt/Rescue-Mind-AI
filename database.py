import sqlite3
import uuid
from datetime import datetime

from config import DATABASE_FILE


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================================
# ID GENERATORS
# =========================================================

def generate_report_id():
    return f"RSM-{uuid.uuid4().hex[:6].upper()}"


def generate_incident_id():
    return f"INC-{uuid.uuid4().hex[:6].upper()}"


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():

    connection = get_connection()
    cursor = connection.cursor()

    # =====================================================
    # USERS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            role TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # EMERGENCY REPORTS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE,
            description TEXT,
            emergency_type TEXT,
            reported_time TEXT,
            submitted_location TEXT,
            latitude REAL,
            longitude REAL,
            reporter_name TEXT,
            reporter_contact TEXT,
            evidence_file_name TEXT,
            evidence_file_type TEXT,
            evidence_data BLOB,
            processing_status TEXT DEFAULT 'Pending AI Analysis',
            transcription_confidence REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # INCIDENTS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE,
            title TEXT,
            description TEXT,
            emergency_type TEXT,
            severity TEXT,
            status TEXT DEFAULT 'Pending',
            source_report_id TEXT,
            ai_summary TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # INCIDENT LOCATIONS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            location_name TEXT,
            latitude REAL,
            longitude REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # INCIDENT EVIDENCE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            file_name TEXT,
            file_type TEXT,
            evidence_data BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # RESOURCES
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_name TEXT,
            resource_type TEXT,
            quantity INTEGER DEFAULT 0,
            available_quantity INTEGER DEFAULT 0,
            location TEXT,
            status TEXT DEFAULT 'Available',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # RESOURCE ASSIGNMENTS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            resource_id INTEGER,
            quantity INTEGER DEFAULT 1,
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Assigned'
        )
    """)

    # =====================================================
    # AGENT EXECUTIONS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            agent_name TEXT,
            input_data TEXT,
            output_data TEXT,
            status TEXT,
            execution_time REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # INCIDENT HISTORY
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT,
            old_status TEXT,
            new_status TEXT,
            changed_by TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # AUDIT LOGS
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            entity_type TEXT,
            entity_id TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # SAFE DATABASE MIGRATION
    # =====================================================

    cursor.execute("""
        PRAGMA table_info(emergency_reports)
    """)

    existing_columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    migration_columns = {

        "report_id": "TEXT",

        "description": "TEXT",

        "emergency_type": "TEXT",

        "reported_time": "TEXT",

        "submitted_location": "TEXT",

        "latitude": "REAL",

        "longitude": "REAL",

        "reporter_name": "TEXT",

        "reporter_contact": "TEXT",

        "evidence_file_name": "TEXT",

        "evidence_file_type": "TEXT",

        "evidence_data": "BLOB",

        "processing_status":
            "TEXT DEFAULT 'Pending AI Analysis'",

        "transcription_confidence": "REAL",

        "created_at": "TEXT"
    }

    for column_name, column_type in migration_columns.items():

        if column_name not in existing_columns:

            try:

                cursor.execute(
                    f"""
                    ALTER TABLE emergency_reports
                    ADD COLUMN {column_name} {column_type}
                    """
                )

            except sqlite3.OperationalError:
                pass

    connection.commit()
    connection.close()


# =========================================================
# SAVE EMERGENCY REPORT
# =========================================================

def save_emergency_report(
    description,
    emergency_type,
    submitted_location,
    latitude=None,
    longitude=None,
    reporter_name=None,
    reporter_contact=None,
    evidence_file_name=None,
    evidence_file_type=None,
    evidence_data=None,
    processing_status="Pending AI Analysis",
    transcription_confidence=None
):

    connection = get_connection()
    cursor = connection.cursor()

    report_id = generate_report_id()

    reported_time = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO emergency_reports (
            report_id,
            description,
            emergency_type,
            reported_time,
            submitted_location,
            latitude,
            longitude,
            reporter_name,
            reporter_contact,
            evidence_file_name,
            evidence_file_type,
            evidence_data,
            processing_status,
            transcription_confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id,
        description,
        emergency_type,
        reported_time,
        submitted_location,
        latitude,
        longitude,
        reporter_name,
        reporter_contact,
        evidence_file_name,
        evidence_file_type,
        evidence_data,
        processing_status,
        transcription_confidence
    ))

    connection.commit()
    connection.close()

    return report_id


# =========================================================
# GET EMERGENCY REPORTS
# =========================================================

def get_emergency_reports(limit=100):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            report_id,
            description,
            emergency_type,
            reported_time,
            submitted_location,
            latitude,
            longitude,
            reporter_name,
            reporter_contact,
            evidence_file_name,
            evidence_file_type,
            processing_status,
            transcription_confidence,
            created_at
        FROM emergency_reports
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    reports = cursor.fetchall()

    connection.close()

    return reports


# =========================================================
# GET SINGLE EMERGENCY REPORT
# =========================================================

def get_emergency_report(report_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM emergency_reports
        WHERE report_id = ?
    """, (report_id,))

    report = cursor.fetchone()

    connection.close()

    return report


# =========================================================
# DATABASE STATISTICS
# =========================================================

def get_database_stats():

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # Emergency reports
    # -----------------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM emergency_reports
    """)

    total_reports = cursor.fetchone()["count"]

    # -----------------------------------------------------
    # Incidents
    # -----------------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM incidents
    """)

    total_incidents = cursor.fetchone()["count"]

    # -----------------------------------------------------
    # Resources
    # -----------------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM resources
    """)

    total_resources = cursor.fetchone()["count"]

    # -----------------------------------------------------
    # Pending reports
    # -----------------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM emergency_reports
        WHERE processing_status = 'Pending AI Analysis'
    """)

    pending_reports = cursor.fetchone()["count"]

    connection.close()

    return {
        "emergency_reports": total_reports,
        "incidents": total_incidents,
        "resources": total_resources,
        "pending_reports": pending_reports
    }


# =========================================================
# UPDATE REPORT STATUS
# =========================================================

def update_report_status(
    report_id,
    new_status
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE emergency_reports
        SET processing_status = ?
        WHERE report_id = ?
    """, (
        new_status,
        report_id
    ))

    connection.commit()
    connection.close()


# =========================================================
# CREATE INCIDENT
# =========================================================

def create_incident(
    title,
    description,
    emergency_type,
    severity="Unknown",
    status="Pending",
    source_report_id=None,
    ai_summary=None
):

    connection = get_connection()
    cursor = connection.cursor()

    incident_id = generate_incident_id()

    cursor.execute("""
        INSERT INTO incidents (
            incident_id,
            title,
            description,
            emergency_type,
            severity,
            status,
            source_report_id,
            ai_summary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_id,
        title,
        description,
        emergency_type,
        severity,
        status,
        source_report_id,
        ai_summary
    ))

    connection.commit()
    connection.close()

    return incident_id


# =========================================================
# GET INCIDENTS
# =========================================================

def get_incidents(limit=100):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM incidents
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    incidents = cursor.fetchall()

    connection.close()

    return incidents


# =========================================================
# ADD RESOURCE
# =========================================================

def add_resource(
    resource_name,
    resource_type,
    quantity,
    location,
    available_quantity=None,
    status="Available"
):

    connection = get_connection()
    cursor = connection.cursor()

    if available_quantity is None:
        available_quantity = quantity

    cursor.execute("""
        INSERT INTO resources (
            resource_name,
            resource_type,
            quantity,
            available_quantity,
            location,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        resource_name,
        resource_type,
        quantity,
        available_quantity,
        location,
        status
    ))

    connection.commit()
    connection.close()


# =========================================================
# GET RESOURCES
# =========================================================

def get_resources(limit=100):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM resources
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    resources = cursor.fetchall()

    connection.close()

    return resources


# =========================================================
# AUDIT LOG
# =========================================================

def add_audit_log(
    action,
    entity_type,
    entity_id,
    details=""
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (
            action,
            entity_type,
            entity_id,
            details
        )
        VALUES (?, ?, ?, ?)
    """, (
        action,
        entity_type,
        entity_id,
        details
    ))

    connection.commit()
    connection.close()


# =========================================================
# GET AUDIT LOGS
# =========================================================

def get_audit_logs(limit=100):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    logs = cursor.fetchall()

    connection.close()

    return logs


# =========================================================
# START DATABASE
# =========================================================

initialize_database()
