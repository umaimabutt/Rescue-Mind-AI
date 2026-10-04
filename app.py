import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st
import folium

from streamlit_folium import st_folium

from config import (
    APP_NAME,
    APP_VERSION,
    INCIDENT_STATUSES,
    EMERGENCY_TYPES,
)

from database import (
    initialize_database,
    save_emergency_report,
    get_emergency_reports,
    get_emergency_report,
    update_report_status,
    create_incident,
    get_incidents,
    get_incident,
    update_incident_status,
    mark_incident_verified,
    add_agent_execution,
    get_agent_executions,
    add_resource,
    get_resources,
    add_resource_assignment,
    get_resource_assignments,
    update_assignment_status,
    add_audit_log,
    get_audit_logs,
    get_database_stats,
)

from ai_engine import get_ai_engine

from agents.emergency_agents import (
    duplicate_candidates,
    severity_fallback,
    match_resources,
    build_response_plan,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# DATABASE
# ============================================================

initialize_database()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 800;
        margin-bottom: 0px;
    }

    .subtitle {
        color: #6b7280;
        font-size: 16px;
        margin-bottom: 20px;
    }

    .status-box {
        padding: 12px;
        border-radius: 10px;
        background-color: #f5f7fa;
        margin-bottom: 10px;
    }

    .warning-box {
        padding: 14px;
        border-radius: 10px;
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
    }

    .success-box {
        padding: 14px;
        border-radius: 10px;
        background-color: #ecfdf5;
        border: 1px solid #a7f3d0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🚨 RescueMind AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    f"""
    <div class="subtitle">
    AI-Powered Emergency Intelligence & Resource Coordination
    &nbsp; | &nbsp; Prototype v{APP_VERSION}
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🚨 RescueMind AI")

st.sidebar.caption(
    "Emergency Intelligence Command Center"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Command Center",
        "Emergency Reports",
        "Incidents",
        "Resources",
        "AI Activity",
        "Audit Trail",
        "Demo Mode",
    ]
)


st.sidebar.divider()

st.sidebar.warning(
    """
    HACKATHON PROTOTYPE

    AI recommendations are not verified emergency facts.

    Human approval is required before operational action.
    """
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def safe_json(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2
        )

    except Exception:
        return str(value)


def run_agent(
    agent_name,
    report_id,
    incident_id,
    function,
    *args
):

    start = time.time()

    try:

        result = function(*args)

        duration = round(
            time.time() - start,
            3
        )

        add_agent_execution(
            agent_name=agent_name,
            status="Completed",
            result=safe_json(result),
            execution_time=duration,
            report_id=report_id,
            incident_id=incident_id,
        )

        return result

    except Exception as exc:

        duration = round(
            time.time() - start,
            3
        )

        add_agent_execution(
            agent_name=agent_name,
            status="Failed",
            result=str(exc),
            execution_time=duration,
            report_id=report_id,
            incident_id=incident_id,
        )

        raise


def get_map_points():

    reports = get_emergency_reports(
        limit=200
    )

    points = []

    for report in reports:

        lat = report.get("latitude")
        lon = report.get("longitude")

        if (
            lat is not None
            and lon is not None
            and float(lat) != 0
            and float(lon) != 0
        ):

            points.append({
                "lat": float(lat),
                "lon": float(lon),
                "type":
                    report.get("emergency_type")
                    or "Emergency",
                "description":
                    report.get("description")
                    or "",
                "report_id":
                    report.get("report_id")
                    or "",
            })

    return points


def create_operations_map():

    points = get_map_points()

    # Lahore as prototype center
    center = [
        31.5204,
        74.3587
    ]

    fmap = folium.Map(
        location=center,
        zoom_start=11,
        control_scale=True
    )


    for point in points:

        popup_text = f"""
        <b>{point['type']}</b><br>
        Report: {point['report_id']}<br>
        {point['description'][:180]}
        """

        folium.Marker(
            location=[
                point["lat"],
                point["lon"]
            ],
            popup=popup_text,
            tooltip=point["type"],
        ).add_to(fmap)


    return fmap


# ============================================================
# AI PIPELINE
# ============================================================

def analyze_report_pipeline(
    report
):

    report_id = report["report_id"]

    # --------------------------------------------------------
    # AI ENGINE
    # --------------------------------------------------------

    engine = get_ai_engine()


    # --------------------------------------------------------
    # AGENT 1: EMERGENCY INTAKE + SEVERITY
    # --------------------------------------------------------

    ai_result = run_agent(
        "Emergency Intake & Severity Agent",
        report_id,
        None,
        engine.analyze_incident,
        report
    )


    # --------------------------------------------------------
    # FALLBACK VALUES
    # --------------------------------------------------------

    if not ai_result.get("category"):

        ai_result["category"] = (
            report.get("emergency_type")
            or "Other"
        )


    if not ai_result.get("severity"):

        fallback = severity_fallback(
            report.get("description", ""),
            report.get("emergency_type", "")
        )

        ai_result["severity"] = (
            fallback["severity"]
        )

        ai_result["severity_score"] = (
            fallback["severity_score"]
        )


    # --------------------------------------------------------
    # AGENT 2: DUPLICATE DETECTION
    # --------------------------------------------------------

    existing_reports = (
        get_emergency_reports(
            limit=200
        )
    )

    candidates = run_agent(
        "Duplicate Detection Agent",
        report_id,
        None,
        duplicate_candidates,
        report,
        existing_reports
    )


    duplicate_group = None

    if candidates:

        duplicate_group = (
            candidates[0]["report_id"]
        )


    # --------------------------------------------------------
    # CREATE INCIDENT
    # --------------------------------------------------------

    incident_id = create_incident(

        report_id=report_id,

        title=ai_result.get(
            "summary",
            "Emergency Incident"
        ),

        description=report.get(
            "description",
            ""
        ),

        emergency_type=ai_result.get(
            "category",
            report.get(
                "emergency_type",
                "Other"
            )
        ),

        severity=ai_result.get(
            "severity",
            "Unknown"
        ),

        severity_score=int(
            ai_result.get(
                "severity_score",
                0
            ) or 0
        ),

        ai_confidence=float(
            ai_result.get(
                "confidence",
                0
            ) or 0
        ),

        people_at_risk=int(
            ai_result.get(
                "people_at_risk",
                0
            ) or 0
        ),

        urgency_reason=ai_result.get(
            "urgency_reason",
            ""
        ),

        missing_information=safe_json(
            ai_result.get(
                "missing_information",
                []
            )
        ),

        recommended_actions=safe_json(
            ai_result.get(
                "recommended_actions",
                []
            )
        ),

        duplicate_group=duplicate_group
    )


    # --------------------------------------------------------
    # AGENT 3: LOCATION INTELLIGENCE
    # --------------------------------------------------------

    location_result = {

        "latitude":
            report.get("latitude"),

        "longitude":
            report.get("longitude"),

        "location":
            report.get(
                "submitted_location"
            ),

        "status":
            "Location captured from report"
    }


    add_agent_execution(
        agent_name="Location Intelligence Agent",
        status="Completed",
        result=safe_json(
            location_result
        ),
        execution_time=0,
        report_id=report_id,
        incident_id=incident_id,
    )


    # --------------------------------------------------------
    # GET RESOURCES
    # --------------------------------------------------------

    resources = get_resources(
        limit=200
    )


    # --------------------------------------------------------
    # AGENT 4: RESOURCE MATCHING
    # --------------------------------------------------------

    incident = get_incident(
        incident_id
    )


    resource_matches = run_agent(
        "Resource Matching Agent",
        report_id,
        incident_id,
        match_resources,
        incident,
        resources
    )


    # --------------------------------------------------------
    # SAVE RECOMMENDATIONS
    # --------------------------------------------------------

    for match in resource_matches[:5]:

        add_resource_assignment(

            incident_id=incident_id,

            resource_id=match[
                "resource_id"
            ],

            match_score=match[
                "match_score"
            ],

            rationale=match[
                "rationale"
            ],

            status="Recommended"
        )


    # --------------------------------------------------------
    # AGENT 5: RESPONSE PLANNING
    # --------------------------------------------------------

    incident = get_incident(
        incident_id
    )

    response_plan = run_agent(
        "Response Planning Agent",
        report_id,
        incident_id,
        build_response_plan,
        incident
    )


    # --------------------------------------------------------
    # ORCHESTRATOR
    # --------------------------------------------------------

    orchestrator_result = {

        "incident_id":
            incident_id,

        "report_id":
            report_id,

        "severity":
            ai_result.get(
                "severity"
            ),

        "duplicate_candidates":
            candidates,

        "resource_matches":
            resource_matches[:5],

        "response_plan":
            response_plan,

        "human_verification_required":
            True
    }


    add_agent_execution(

        agent_name="Orchestrator",

        status="Completed",

        result=safe_json(
            orchestrator_result
        ),

        execution_time=0,

        report_id=report_id,

        incident_id=incident_id,
    )


    update_report_status(
        report_id,
        "AI Analysis Complete"
    )


    add_audit_log(

        action="Incident Created",

        entity_type="Incident",

        entity_id=incident_id,

        user_name="AI Orchestrator",

        details=(
            f"Created from report "
            f"{report_id}. "
            f"Human verification required."
        )
    )


    return {

        "incident_id":
            incident_id,

        "ai_result":
            ai_result,

        "duplicates":
            candidates,

        "resource_matches":
            resource_matches,

        "response_plan":
            response_plan,
    }


# ============================================================
# COMMAND CENTER
# ============================================================

if page == "Command Center":

    st.header("🛰️ Emergency Command Center")

    stats = get_database_stats()


    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    col1, col2, col3, col4, col5 = st.columns(5)


    col1.metric(
        "Emergency Reports",
        stats["emergency_reports"]
    )

    col2.metric(
        "Incidents",
        stats["incidents"]
    )

    col3.metric(
        "Critical",
        stats["critical_incidents"]
    )

    col4.metric(
        "Active Incidents",
        stats["active_incidents"]
    )

    col5.metric(
        "Resources",
        stats["resources"]
    )


    st.divider()


    # --------------------------------------------------------
    # MAP
    # --------------------------------------------------------

    st.subheader(
        "📍 Operations Map"
    )

    points = get_map_points()

    if points:

        fmap = create_operations_map()

        st_folium(
            fmap,
            width=None,
            height=500
        )

    else:

        st.info(
            "No emergency locations available yet. "
            "Submit a report with latitude and longitude "
            "to display it on the map."
        )


    # --------------------------------------------------------
    # RECENT INCIDENTS
    # --------------------------------------------------------

    st.subheader(
        "🚨 Recent Incidents"
    )

    incidents = get_incidents(
        limit=10
    )

    if incidents:

        df = pd.DataFrame(
            incidents
        )

        columns = [
            "incident_id",
            "emergency_type",
            "severity",
            "severity_score",
            "status",
            "human_verified",
            "created_at",
        ]

        available = [
            c for c in columns
            if c in df.columns
        ]

        st.dataframe(
            df[available],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No incidents created yet."
        )


# ============================================================
# EMERGENCY REPORTS
# ============================================================

elif page == "Emergency Reports":

    st.header(
        "📥 Emergency Intake"
    )

    st.write(
        "Submit a citizen emergency report "
        "for AI-powered analysis."
    )


    st.markdown(
        """
        <div class="warning-box">

        ⚠️ AI-generated assessments are recommendations only.
        Emergency personnel must verify information before action.

        </div>
        """,
        unsafe_allow_html=True
    )


    st.divider()


    # --------------------------------------------------------
    # REPORT FORM
    # --------------------------------------------------------

    with st.form(
        "emergency_report_form"
    ):

        col1, col2 = st.columns(2)


        with col1:

            emergency_type = st.selectbox(
                "Emergency Type",
                EMERGENCY_TYPES
            )

            reporter_name = st.text_input(
                "Reporter Name"
            )

            reporter_contact = st.text_input(
                "Reporter Contact"
            )

            location = st.text_input(
                "Location / Address"
            )


        with col2:

            latitude = st.number_input(
                "Latitude",
                value=0.0,
                format="%.6f"
            )

            longitude = st.number_input(
                "Longitude",
                value=0.0,
                format="%.6f"
            )

            reported_time = st.text_input(
                "Reported Time",
                value=datetime.now().isoformat(
                    timespec="minutes"
                )
            )


        description = st.text_area(
            "Emergency Description",
            height=180,
            placeholder=(
                "Example: Several people are trapped "
                "inside a flooded building..."
            )
        )


        uploaded_file = st.file_uploader(
            "Upload Evidence Image / File",
            type=[
                "png",
                "jpg",
                "jpeg",
                "pdf",
                "txt"
            ]
        )


        audio_file = st.file_uploader(
            "Optional Voice Emergency Report",
            type=[
                "wav",
                "mp3",
                "m4a",
                "ogg"
            ]
        )


        submitted = st.form_submit_button(
            "🚨 Submit Emergency Report",
            use_container_width=True
        )


    # --------------------------------------------------------
    # PROCESS REPORT
    # --------------------------------------------------------

    if submitted:

        if not description.strip() and not audio_file:

            st.error(
                "Please provide an emergency description "
                "or voice report."
            )

        else:

            transcription_confidence = None

            # ---------------------------------------------
            # VOICE TRANSCRIPTION
            # ---------------------------------------------

            if audio_file:

                try:

                    with st.spinner(
                        "🎙️ Transcribing emergency voice report..."
                    ):

                        engine = get_ai_engine()

                        transcription = (
                            engine.transcribe_audio(
                                audio_file.getvalue(),
                                audio_file.name
                            )
                        )


                    voice_text = (
                        transcription.get(
                            "text",
                            ""
                        )
                    )


                    if voice_text:

                        if description.strip():

                            description = (
                                description
                                + "\n\n"
                                + "AI Voice Transcript:\n"
                                + voice_text
                            )

                        else:

                            description = voice_text


                        st.info(
                            "🎙️ Voice transcript generated by AI. "
                            "Human verification is required."
                        )

                        transcription_confidence = (
                            transcription.get(
                                "confidence"
                            )
                        )

                except Exception as exc:

                    st.error(
                        f"Voice transcription failed: {exc}"
                    )


            # ---------------------------------------------
            # SAVE REPORT
            # ---------------------------------------------

            evidence_data = None
            evidence_name = None
            evidence_type = None

            if uploaded_file:

                evidence_data = (
                    uploaded_file.getvalue()
                )

                evidence_name = (
                    uploaded_file.name
                )

                evidence_type = (
                    uploaded_file.type
                )


            lat_value = (
                latitude
                if latitude != 0
                else None
            )

            lon_value = (
                longitude
                if longitude != 0
                else None
            )


            report_id = save_emergency_report(

                description=description,

                emergency_type=emergency_type,

                reported_time=reported_time,

                submitted_location=location,

                latitude=lat_value,

                longitude=lon_value,

                reporter_name=reporter_name,

                reporter_contact=reporter_contact,

                evidence_file_name=evidence_name,

                evidence_file_type=evidence_type,

                evidence_data=evidence_data,

                transcription_confidence=(
                    transcription_confidence
                )
            )


            add_audit_log(

                action="Emergency Report Submitted",

                entity_type="Emergency Report",

                entity_id=report_id,

                user_name=(
                    reporter_name
                    or "Citizen"
                ),

                details=(
                    "New emergency report submitted."
                )
            )


            st.success(
                f"Report submitted successfully: {report_id}"
            )


            # ---------------------------------------------
            # ANALYZE
            # ---------------------------------------------

            report = get_emergency_report(
                report_id
            )


            with st.spinner(
                "🤖 RescueMind AI is analyzing the report..."
            ):

                try:

                    result = (
                        analyze_report_pipeline(
                            report
                        )
                    )


                    st.success(
                        "AI emergency analysis completed."
                    )


                    # -----------------------------------------
                    # RESULTS
                    # -----------------------------------------

                    ai_result = (
                        result["ai_result"]
                    )


                    col1, col2, col3, col4 = st.columns(4)


                    col1.metric(
                        "Category",
                        ai_result.get(
                            "category",
                            "Unknown"
                        )
                    )

                    col2.metric(
                        "Severity",
                        ai_result.get(
                            "severity",
                            "Unknown"
                        )
                    )

                    col3.metric(
                        "Severity Score",
                        ai_result.get(
                            "severity_score",
                            0
                        )
                    )

                    col4.metric(
                        "Confidence",
                        f"{float(ai_result.get('confidence', 0) or 0) * 100:.0f}%"
                    )


                    st.subheader(
                        "🧠 AI Assessment"
                    )


                    st.write(
                        ai_result.get(
                            "summary",
                            "No summary available."
                        )
                    )


                    st.markdown(
                        "**Urgency Reason**"
                    )

                    st.write(
                        ai_result.get(
                            "urgency_reason",
                            "Not provided."
                        )
                    )


                    st.markdown(
                        "**Detected Signals**"
                    )

                    signals = ai_result.get(
                        "detected_signals",
                        []
                    )

                    if signals:

                        for item in signals:

                            st.write(
                                f"• {item}"
                            )

                    else:

                        st.write(
                            "No signals reported."
                        )


                    st.markdown(
                        "**Missing Information**"
                    )

                    missing = ai_result.get(
                        "missing_information",
                        []
                    )

                    if missing:

                        for item in missing:

                            st.write(
                                f"• {item}"
                            )

                    else:

                        st.write(
                            "No missing information identified."
                        )


                    st.markdown(
                        "**Recommended Actions**"
                    )

                    actions = ai_result.get(
                        "recommended_actions",
                        []
                    )

                    if actions:

                        for item in actions:

                            st.write(
                                f"• {item}"
                            )


                    # -----------------------------------------
                    # DUPLICATES
                    # -----------------------------------------

                    st.subheader(
                        "🔎 Duplicate Detection"
                    )

                    duplicates = (
                        result["duplicates"]
                    )

                    if duplicates:

                        st.warning(
                            "Potential duplicate reports detected. "
                            "Human approval is required before merging."
                        )

                        st.dataframe(
                            pd.DataFrame(
                                duplicates
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                    else:

                        st.success(
                            "No strong duplicate candidate detected."
                        )


                    # -----------------------------------------
                    # RESOURCE MATCHING
                    # -----------------------------------------

                    st.subheader(
                        "🚑 Recommended Resources"
                    )

                    matches = (
                        result[
                            "resource_matches"
                        ]
                    )

                    if matches:

                        st.dataframe(
                            pd.DataFrame(
                                matches
                            ),
                            use_container_width=True,
                            hide_index=True
                        )

                    else:

                        st.info(
                            "No matching resources are currently available."
                        )


                    # -----------------------------------------
                    # RESPONSE PLAN
                    # -----------------------------------------

                    st.subheader(
                        "📋 Response Plan"
                    )

                    for action in result[
                        "response_plan"
                    ]:

                        st.write(
                            f"• {action}"
                        )


                    st.info(
                        f"Incident created: "
                        f"{result['incident_id']}"
                    )


                except Exception as exc:

                    st.error(
                        f"AI analysis failed: {exc}"
                    )


# ============================================================
# INCIDENTS
# ============================================================

elif page == "Incidents":

    st.header(
        "🚨 Incident Management"
    )


    incidents = get_incidents(
        limit=200
    )


    if not incidents:

        st.info(
            "No incidents available."
        )

    else:

        for incident in incidents:

            with st.container(
                border=True
            ):

                col1, col2, col3, col4 = st.columns(4)


                col1.write(
                    f"**{incident['incident_id']}**"
                )

                col2.write(
                    f"**{incident['emergency_type']}**"
                )

                col3.write(
                    f"**Severity:** {incident['severity']}"
                )

                col4.write(
                    f"**Status:** {incident['status']}"
                )


                st.write(
                    incident.get(
                        "description",
                        ""
                    )
                )


                st.caption(
                    f"Severity Score: "
                    f"{incident.get('severity_score', 0)} "
                    f"| People at Risk: "
                    f"{incident.get('people_at_risk', 0)} "
                    f"| AI Confidence: "
                    f"{float(incident.get('ai_confidence', 0) or 0) * 100:.0f}%"
                )


                st.markdown(
                    "**Urgency Reason:**"
                )

                st.write(
                    incident.get(
                        "urgency_reason",
                        ""
                    )
                )


                col_a, col_b, col_c = st.columns(3)


                with col_a:

                    status = st.selectbox(
                        "Update Status",
                        INCIDENT_STATUSES,
                        index=(
                            INCIDENT_STATUSES.index(
                                incident["status"]
                            )
                            if incident["status"]
                            in INCIDENT_STATUSES
                            else 0
                        ),
                        key=f"status_{incident['incident_id']}"
                    )


                with col_b:

                    if st.button(
                        "Update Status",
                        key=f"update_{incident['incident_id']}"
                    ):

                        update_incident_status(
                            incident["incident_id"],
                            status
                        )

                        add_audit_log(
                            action="Incident Status Updated",
                            entity_type="Incident",
                            entity_id=incident["incident_id"],
                            user_name="Command Center",
                            details=f"New status: {status}"
                        )

                        st.success(
                            "Status updated."
                        )

                        st.rerun()


                with col_c:

                    verified = bool(
                        incident.get(
                            "human_verified",
                            0
                        )
                    )

                    if not verified:

                        if st.button(
                            "✅ Human Verify",
                            key=f"verify_{incident['incident_id']}"
                        ):

                            mark_incident_verified(
                                incident["incident_id"],
                                True
                            )

                            add_audit_log(
                                action="Human Verification",
                                entity_type="Incident",
                                entity_id=incident["incident_id"],
                                user_name="Command Center",
                                details="Incident manually verified."
                            )

                            st.success(
                                "Incident marked as human verified."
                            )

                            st.rerun()

                    else:

                        st.success(
                            "Human Verified"
                        )


                assignments = (
                    get_resource_assignments(
                        incident["incident_id"]
                    )
                )


                if assignments:

                    st.markdown(
                        "**Resource Recommendations**"
                    )

                    st.dataframe(
                        pd.DataFrame(
                            assignments
                        ),
                        use_container_width=True,
                        hide_index=True
                    )


# ============================================================
# RESOURCES
# ============================================================

elif page == "Resources":

    st.header(
        "🚑 Resource Management"
    )


    resources = get_resources(
        limit=200
    )


    if resources:

        st.subheader(
            "Available Resources"
        )

        st.dataframe(
            pd.DataFrame(
                resources
            ),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No resources have been added yet."
        )


    st.divider()


    st.subheader(
        "➕ Add Resource"
    )


    with st.form(
        "resource_form"
    ):

        col1, col2 = st.columns(2)


        with col1:

            name = st.text_input(
                "Resource Name"
            )

            resource_type = st.selectbox(
                "Resource Type",
                [
                    "Ambulance",
                    "Fire Truck",
                    "Rescue Team",
                    "Boat",
                    "Search & Rescue",
                    "Medical Team",
                    "Supply Unit",
                    "Other"
                ]
            )


        with col2:

            status = st.selectbox(
                "Status",
                [
                    "Available",
                    "Ready",
                    "Standby",
                    "Busy",
                    "Unavailable"
                ]
            )

            capacity = st.number_input(
                "Capacity",
                min_value=0,
                value=1
            )


        col3, col4 = st.columns(2)


        with col3:

            resource_latitude = st.number_input(
                "Latitude",
                value=0.0,
                format="%.6f"
            )


        with col4:

            resource_longitude = st.number_input(
                "Longitude",
                value=0.0,
                format="%.6f"
            )


        contact = st.text_input(
            "Contact"
        )


        resource_submit = st.form_submit_button(
            "Add Resource",
            use_container_width=True
        )


    if resource_submit:

        add_resource(

            name=name,

            resource_type=resource_type,

            status=status,

            capacity=capacity,

            latitude=(
                resource_latitude
                if resource_latitude != 0
                else None
            ),

            longitude=(
                resource_longitude
                if resource_longitude != 0
                else None
            ),

            contact=contact
        )


        add_audit_log(
            action="Resource Added",
            entity_type="Resource",
            entity_id=name,
            user_name="Command Center",
            details=f"{resource_type} added."
        )


        st.success(
            "Resource added successfully."
        )

        st.rerun()


# ============================================================
# AI ACTIVITY
# ============================================================

elif page == "AI Activity":

    st.header(
        "🤖 Multi-Agent AI Activity"
    )


    executions = get_agent_executions(
        limit=200
    )


    if executions:

        df = pd.DataFrame(
            executions
        )

        columns = [
            "agent_name",
            "status",
            "report_id",
            "incident_id",
            "execution_time",
            "created_at",
        ]

        available = [
            c for c in columns
            if c in df.columns
        ]

        st.dataframe(
            df[available],
            use_container_width=True,
            hide_index=True
        )


        st.subheader(
            "Agent Details"
        )


        for execution in executions[:20]:

            with st.expander(
                f"{execution['agent_name']} — "
                f"{execution['status']}"
            ):

                st.write(
                    execution.get(
                        "result",
                        ""
                    )
                )

    else:

        st.info(
            "No AI agent executions yet."
        )


# ============================================================
# AUDIT TRAIL
# ============================================================

elif page == "Audit Trail":

    st.header(
        "📜 Audit Trail"
    )


    logs = get_audit_logs(
        limit=200
    )


    if logs:

        st.dataframe(
            pd.DataFrame(
                logs
            ),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No audit events recorded yet."
        )


# ============================================================
# DEMO MODE
# ============================================================

elif page == "Demo Mode":

    st.header(
        "🎬 RescueMind AI Demo Mode"
    )


    st.write(
        """
        Use this page to prepare a hackathon demonstration.

        Recommended demo flow:

        1. Add emergency resources.
        2. Submit multiple reports.
        3. Let AI classify the incidents.
        4. Show severity assessment.
        5. Show duplicate detection.
        6. Show resource recommendations.
        7. Human-verify an incident.
        8. Assign/update its status.
        9. Show the command dashboard.
        """
    )


    st.divider()


    st.subheader(
        "🚑 Seed Demo Resources"
    )


    if st.button(
        "Create Demo Resources",
        use_container_width=True
    ):

        existing = get_resources(
            limit=1
        )


        if existing:

            st.info(
                "Resources already exist."
            )

        else:

            demo_resources = [

                (
                    "Lahore Rescue Ambulance 01",
                    "Ambulance",
                    "Available",
                    2,
                    31.5204,
                    74.3587,
                    "1122"
                ),

                (
                    "Lahore Fire Unit 01",
                    "Fire Truck",
                    "Available",
                    6,
                    31.5150,
                    74.3500,
                    "1122"
                ),

                (
                    "Flood Rescue Team Alpha",
                    "Rescue Team",
                    "Available",
                    8,
                    31.5000,
                    74.3600,
                    "1122"
                ),

                (
                    "Emergency Boat 01",
                    "Boat",
                    "Available",
                    10,
                    31.5100,
                    74.3700,
                    "1122"
                ),

                (
                    "Search Rescue Team 01",
                    "Search & Rescue",
                    "Available",
                    12,
                    31.5300,
                    74.3400,
                    "1122"
                ),

                (
                    "Emergency Medical Team 01",
                    "Medical Team",
                    "Available",
                    5,
                    31.5250,
                    74.3650,
                    "1122"
                ),
            ]


            for item in demo_resources:

                add_resource(
                    name=item[0],
                    resource_type=item[1],
                    status=item[2],
                    capacity=item[3],
                    latitude=item[4],
                    longitude=item[5],
                    contact=item[6]
                )


            add_audit_log(
                action="Demo Resources Created",
                entity_type="System",
                entity_id="DEMO",
                user_name="Hackathon Demo",
                details="Demo resource dataset created."
            )


            st.success(
                "Demo resources created successfully."
            )

            st.rerun()


    st.divider()


    st.subheader(
        "🧪 Demo Scenario"
    )


    st.info(
        """
        Suggested scenario:

        Flood emergency:
        "Heavy flooding has affected several houses.
        Water is entering the buildings and some people
        may be trapped."

        Submit this report from Emergency Reports.

        Then submit another similar report from a nearby
        location to demonstrate duplicate detection.
        """
    )


    st.divider()


    st.subheader(
        "📊 Current Demo Statistics"
    )


    stats = get_database_stats()


    col1, col2, col3 = st.columns(3)


    col1.metric(
        "Reports",
        stats["emergency_reports"]
    )

    col2.metric(
        "Incidents",
        stats["incidents"]
    )

    col3.metric(
        "Resources",
        stats["resources"]
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "RescueMind AI — Hackathon Prototype | "
    "AI recommendations require human verification."
)
