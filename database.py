import sqlite3
import uuid
from datetime import datetime

from config import DATABASE_FILE


def get_connection():
    """Create a connection to the RescueMind SQLite database."""

    connection = sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def generate_report_id():
    """Generate a unique citizen emergency report ID."""

    unique_part = uuid.uuid4().hex[:6].upper()

    return f"RSM-{unique_part}"


def generate_incident_id():
    """Generate a unique incident ID."""

    unique_part = uuid.uuid4().hex[:6].upper()

    return f"INC-{unique_part}"


def initialize_database():
    """Create all RescueMind AI database tables."""

    connection = get_connection()
    cursor = connection.cursor()

    # --------------------------------------------------
    # USERS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            role TEXT NOT NULL DEFAULT 'admin',
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------
    # EMERGENCY REPORTS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emergency_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
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
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------
    # INCIDENTS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            emergency_type TEXT,
            description TEXT,
            severity TEXT DEFAULT 'Unknown',
            status TEXT DEFAULT 'Pending',
            ai_summary TEXT,
            human_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------
    # INCIDENT LOCATIONS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            address TEXT,
            landmark TEXT,
            latitude REAL,
            longitude REAL,
            confidence REAL,
            verified INTEGER DEFAULT 0,
            FOREIGN KEY (incident_id)
                REFERENCES incidents(id)
        )
    """)

    # --------------------------------------------------
    # INCIDENT EVIDENCE
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            evidence_type TEXT,
            file_name TEXT,
            file_path TEXT,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (incident_id)
                REFERENCES incidents(id)
        )
    """)

    # --------------------------------------------------
    # RESOURCES
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            capacity INTEGER DEFAULT 0,
            availability TEXT DEFAULT 'Available',
            latitude REAL,
            longitude REAL,
            location_name TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # --------------------------------------------------
    # RESOURCE ASSIGNMENTS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            status TEXT DEFAULT 'Proposed',
            reason TEXT,
            approved_by INTEGER,
            assigned_at TEXT,
            FOREIGN KEY (incident_id)
                REFERENCES incidents(id),
            FOREIGN KEY (resource_id)
                REFERENCES resources(id)
        )
    """)

    # --------------------------------------------------
    # AI AGENT EXECUTIONS
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER,
            agent_name TEXT NOT NULL,
            status TEXT NOT NULL,
            input_summary TEXT,
            output_summary TEXT,
            execution_time REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (incident_id)
                REFERENCES incidents(id)
        )
    """)

    # --------------------------------------------------
    # INCIDENT HISTORY
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT,
            changed_by TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (incident_id)
                REFERENCES incidents(id)
        )
    """)

    # --------------------------------------------------
    # AUDIT LOG
    # --------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            performed_by TEXT,
            details TEXT,
            created_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_emergency_report(
    description,
    emergency_type,
    reported_time,
    location,
    latitude=None,
    longitude=None,
    reporter_name=None,
    reporter_contact=None,
    evidence_file_name=None,
    evidence_file_type=None,
    evidence_data=None,
):
    """Save a new emergency report."""

    report_id = generate_report_id()

    connection = get_connection()
    cursor = connection.cursor()

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
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_id,
        description,
        emergency_type,
        reported_time,
        location,
        latitude,
        longitude,
        reporter_name,
        reporter_contact,
        evidence_file_name,
        evidence_file_type,
        evidence_data,
        "Pending AI Analysis",
        datetime.utcnow().isoformat(),
    ))

    connection.commit()
    connection.close()

    add_audit_log(
        action="Emergency report submitted",
        entity_type="emergency_report",
        entity_id=report_id,
        performed_by="citizen",
        details=f"Emergency type: {emergency_type}",
    )

    return report_id


def get_emergency_reports(limit=100):
    """Retrieve recent emergency reports."""

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

    reports = [dict(row) for row in cursor.fetchall()]

    connection.close()

    return reports


def get_database_stats():
    """Return basic database statistics."""

    connection = get_connection()
    cursor = connection.cursor()

    tables = [
        "emergency_reports",
        "incidents",
        "resources",
        "resource_assignments",
        "agent_executions",
        "audit_logs",
    ]

    stats = {}

    for table in tables:
        cursor.execute(
            f"SELECT COUNT(*) FROM {table}"
        )

        stats[table] = cursor.fetchone()[0]

    connection.close()

    return stats


def add_audit_log(
    action,
    entity_type=None,
    entity_id=None,
    performed_by="system",
    details=None,
):
    """Record an important system action."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO audit_logs (
            action,
            entity_type,
            entity_id,
            performed_by,
            details,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        action,
        entity_type,
        entity_id,
        performed_by,
        details,
        datetime.utcnow().isoformat(),
    ))

    connection.commit()
    connection.close()
