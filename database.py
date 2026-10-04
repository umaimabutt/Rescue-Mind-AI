import sqlite3
import uuid
from datetime import datetime

from config import DATABASE_FILE


def get_connection():

    connection = sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


def generate_report_id():

    return "RPT-" + uuid.uuid4().hex[:8].upper()


def generate_incident_id():

    return "INC-" + uuid.uuid4().hex[:8].upper()


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    # -----------------------------------------
    # USERS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            contact TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # EMERGENCY REPORTS
    # -----------------------------------------

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


    # -----------------------------------------
    # INCIDENTS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT UNIQUE,

            report_id TEXT,

            title TEXT,

            description TEXT,

            emergency_type TEXT,

            severity TEXT,

            severity_score INTEGER DEFAULT 0,

            ai_confidence REAL,

            duplicate_group TEXT,

            people_at_risk INTEGER DEFAULT 0,

            urgency_reason TEXT,

            missing_information TEXT,

            recommended_actions TEXT,

            human_verified INTEGER DEFAULT 0,

            status TEXT DEFAULT 'Pending',

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # INCIDENT LOCATIONS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_locations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT,

            latitude REAL,

            longitude REAL,

            address TEXT,

            location_source TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # EVIDENCE
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_evidence (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT,

            file_name TEXT,

            file_type TEXT,

            evidence_data BLOB,

            source TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # RESOURCES
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            resource_type TEXT,

            status TEXT,

            capacity INTEGER DEFAULT 0,

            latitude REAL,

            longitude REAL,

            contact TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # RESOURCE ASSIGNMENTS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_assignments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT,

            resource_id INTEGER,

            match_score REAL DEFAULT 0,

            rationale TEXT,

            status TEXT DEFAULT 'Recommended',

            assigned_at TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # AGENT EXECUTIONS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_executions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            report_id TEXT,

            incident_id TEXT,

            agent_name TEXT,

            status TEXT,

            result TEXT,

            execution_time REAL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # INCIDENT HISTORY
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incident_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT,

            old_status TEXT,

            new_status TEXT,

            changed_by TEXT,

            note TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    # -----------------------------------------
    # AUDIT LOGS
    # -----------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            action TEXT,

            entity_type TEXT,

            entity_id TEXT,

            user_name TEXT,

            details TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)


    connection.commit()

    # Run migrations for older versions
    _run_migrations(connection)

    connection.close()


def _run_migrations(connection):

    cursor = connection.cursor()

    migrations = {

        "emergency_reports": {

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

            "created_at":
                "TEXT DEFAULT CURRENT_TIMESTAMP",
        },

        "incidents": {

            "severity_score":
                "INTEGER DEFAULT 0",

            "ai_confidence":
                "REAL",

            "duplicate_group":
                "TEXT",

            "people_at_risk":
                "INTEGER DEFAULT 0",

            "urgency_reason":
                "TEXT",

            "missing_information":
                "TEXT",

            "recommended_actions":
                "TEXT",

            "human_verified":
                "INTEGER DEFAULT 0",

            "updated_at":
                "TEXT DEFAULT CURRENT_TIMESTAMP",
        },

        "resources": {

            "latitude": "REAL",

            "longitude": "REAL",
        },

        "resource_assignments": {

            "match_score":
                "REAL DEFAULT 0",

            "rationale":
                "TEXT",
        },

        "agent_executions": {

            "report_id":
                "TEXT",
        }
    }


    for table, columns in migrations.items():

        existing = cursor.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()

        existing_names = {
            row["name"]
            for row in existing
        }

        for column, definition in columns.items():

            if column not in existing_names:

                try:

                    cursor.execute(
                        f"""
                        ALTER TABLE {table}
                        ADD COLUMN {column}
                        {definition}
                        """
                    )

                except Exception:
                    pass

    connection.commit()


# =========================================
# EMERGENCY REPORTS
# =========================================

def save_emergency_report(
    description,
    emergency_type,
    reported_time,
    submitted_location,
    latitude,
    longitude,
    reporter_name,
    reporter_contact,
    evidence_file_name=None,
    evidence_file_type=None,
    evidence_data=None,
    transcription_confidence=None
):

    connection = get_connection()

    cursor = connection.cursor()

    report_id = generate_report_id()

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
        "Pending AI Analysis",
        transcription_confidence
    ))

    connection.commit()

    connection.close()

    return report_id


def get_emergency_reports(limit=100):

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM emergency_reports
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def get_emergency_report(report_id):

    connection = get_connection()

    row = connection.execute("""
        SELECT *
        FROM emergency_reports
        WHERE report_id = ?
    """, (report_id,)).fetchone()

    connection.close()

    return dict(row) if row else None


def update_report_status(
    report_id,
    status
):

    connection = get_connection()

    connection.execute("""
        UPDATE emergency_reports

        SET processing_status = ?

        WHERE report_id = ?
    """, (
        status,
        report_id
    ))

    connection.commit()

    connection.close()


# =========================================
# INCIDENTS
# =========================================

def create_incident(
    report_id,
    title,
    description,
    emergency_type,
    severity,
    severity_score,
    ai_confidence,
    people_at_risk,
    urgency_reason,
    missing_information,
    recommended_actions,
    duplicate_group=None
):

    connection = get_connection()

    cursor = connection.cursor()

    incident_id = generate_incident_id()

    cursor.execute("""
        INSERT INTO incidents (

            incident_id,
            report_id,
            title,
            description,
            emergency_type,
            severity,
            severity_score,
            ai_confidence,
            duplicate_group,
            people_at_risk,
            urgency_reason,
            missing_information,
            recommended_actions,
            human_verified,
            status

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        incident_id,
        report_id,
        title,
        description,
        emergency_type,
        severity,
        severity_score,
        ai_confidence,
        duplicate_group,
        people_at_risk,
        urgency_reason,
        missing_information,
        recommended_actions,
        0,
        "Pending"
    ))

    connection.commit()

    connection.close()

    return incident_id


def get_incidents(limit=100):

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM incidents
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def get_incident(incident_id):

    connection = get_connection()

    row = connection.execute("""
        SELECT *
        FROM incidents
        WHERE incident_id = ?
    """, (incident_id,)).fetchone()

    connection.close()

    return dict(row) if row else None


def update_incident_status(
    incident_id,
    new_status,
    changed_by="Command Center",
    note=""
):

    connection = get_connection()

    row = connection.execute("""
        SELECT status
        FROM incidents
        WHERE incident_id = ?
    """, (incident_id,)).fetchone()

    if not row:
        connection.close()
        return False

    old_status = row["status"]

    connection.execute("""
        UPDATE incidents

        SET status = ?,
            updated_at = ?

        WHERE incident_id = ?
    """, (

        new_status,
        datetime.now().isoformat(),
        incident_id
    ))


    connection.execute("""
        INSERT INTO incident_history (

            incident_id,
            old_status,
            new_status,
            changed_by,
            note

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        incident_id,
        old_status,
        new_status,
        changed_by,
        note
    ))


    connection.commit()

    connection.close()

    return True


def mark_incident_verified(
    incident_id,
    verified=True
):

    connection = get_connection()

    connection.execute("""
        UPDATE incidents

        SET human_verified = ?,
            updated_at = ?

        WHERE incident_id = ?
    """, (

        1 if verified else 0,
        datetime.now().isoformat(),
        incident_id
    ))

    connection.commit()

    connection.close()


# =========================================
# AGENT EXECUTIONS
# =========================================

def add_agent_execution(
    agent_name,
    status,
    result,
    execution_time=0,
    report_id=None,
    incident_id=None
):

    connection = get_connection()

    connection.execute("""
        INSERT INTO agent_executions (

            report_id,
            incident_id,
            agent_name,
            status,
            result,
            execution_time

        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        report_id,
        incident_id,
        agent_name,
        status,
        result,
        execution_time
    ))

    connection.commit()

    connection.close()


def get_agent_executions(limit=100):

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM agent_executions
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# =========================================
# RESOURCES
# =========================================

def add_resource(
    name,
    resource_type,
    status="Available",
    capacity=0,
    latitude=None,
    longitude=None,
    contact=""
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO resources (

            name,
            resource_type,
            status,
            capacity,
            latitude,
            longitude,
            contact

        )

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (

        name,
        resource_type,
        status,
        capacity,
        latitude,
        longitude,
        contact
    ))

    connection.commit()

    resource_id = cursor.lastrowid

    connection.close()

    return resource_id


def get_resources(limit=100):

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM resources
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# =========================================
# RESOURCE ASSIGNMENTS
# =========================================

def add_resource_assignment(
    incident_id,
    resource_id,
    match_score,
    rationale,
    status="Recommended"
):

    connection = get_connection()

    connection.execute("""
        INSERT INTO resource_assignments (

            incident_id,
            resource_id,
            match_score,
            rationale,
            status,
            assigned_at

        )

        VALUES (?, ?, ?, ?, ?, ?)
    """, (

        incident_id,
        resource_id,
        match_score,
        rationale,
        status,
        datetime.now().isoformat()
    ))

    connection.commit()

    connection.close()


def get_resource_assignments(
    incident_id=None,
    limit=100
):

    connection = get_connection()

    if incident_id:

        rows = connection.execute("""
            SELECT
                ra.*,
                r.name AS resource_name,
                r.resource_type,
                r.status AS resource_status

            FROM resource_assignments ra

            LEFT JOIN resources r
                ON ra.resource_id = r.id

            WHERE ra.incident_id = ?

            ORDER BY ra.match_score DESC

            LIMIT ?
        """, (
            incident_id,
            limit
        )).fetchall()

    else:

        rows = connection.execute("""
            SELECT
                ra.*,
                r.name AS resource_name,
                r.resource_type,
                r.status AS resource_status

            FROM resource_assignments ra

            LEFT JOIN resources r
                ON ra.resource_id = r.id

            ORDER BY ra.id DESC

            LIMIT ?
        """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


def update_assignment_status(
    assignment_id,
    status
):

    connection = get_connection()

    connection.execute("""
        UPDATE resource_assignments

        SET status = ?

        WHERE id = ?
    """, (

        status,
        assignment_id
    ))

    connection.commit()

    connection.close()


# =========================================
# AUDIT
# =========================================

def add_audit_log(
    action,
    entity_type,
    entity_id,
    user_name="System",
    details=""
):

    connection = get_connection()

    connection.execute("""
        INSERT INTO audit_logs (

            action,
            entity_type,
            entity_id,
            user_name,
            details

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        action,
        entity_type,
        entity_id,
        user_name,
        details
    ))

    connection.commit()

    connection.close()


def get_audit_logs(limit=100):

    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM audit_logs

        ORDER BY id DESC

        LIMIT ?
    """, (limit,)).fetchall()

    connection.close()

    return [dict(row) for row in rows]


# =========================================
# DATABASE STATISTICS
# =========================================

def get_database_stats():

    connection = get_connection()

    emergency_reports = connection.execute("""
        SELECT COUNT(*)
        FROM emergency_reports
    """).fetchone()[0]


    incidents = connection.execute("""
        SELECT COUNT(*)
        FROM incidents
    """).fetchone()[0]


    resources = connection.execute("""
        SELECT COUNT(*)
        FROM resources
    """).fetchone()[0]


    agent_executions = connection.execute("""
        SELECT COUNT(*)
        FROM agent_executions
    """).fetchone()[0]


    critical_incidents = connection.execute("""
        SELECT COUNT(*)
        FROM incidents
        WHERE severity = 'Critical'
    """).fetchone()[0]


    active_incidents = connection.execute("""
        SELECT COUNT(*)
        FROM incidents
        WHERE status NOT IN ('Resolved')
    """).fetchone()[0]


    connection.close()


    return {

        "emergency_reports":
            emergency_reports,

        "incidents":
            incidents,

        "resources":
            resources,

        "agent_executions":
            agent_executions,

        "critical_incidents":
            critical_incidents,

        "active_incidents":
            active_incidents,
    }
