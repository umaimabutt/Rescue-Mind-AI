import streamlit as st
from datetime import datetime

from config import (
    APP_NAME,
    APP_VERSION,
    INCIDENT_STATUSES,
    EMERGENCY_TYPES,
)

from database import (
    initialize_database,
    get_database_stats,
    get_emergency_reports,
    save_emergency_report,
)


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==================================================
# DATABASE
# ==================================================

initialize_database()


# ==================================================
# CSS
# ==================================================

st.markdown("""
<style>

.main {
    background-color: #f5f7fa;
}

.block-container {
    padding-top: 2rem;
}

.header-title {
    font-size: 34px;
    font-weight: 700;
}

.header-subtitle {
    color: #6b7280;
    font-size: 16px;
}

.report-card {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    margin-bottom: 12px;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# SIDEBAR
# ==================================================

with st.sidebar:

    st.markdown("# 🚨 RescueMind AI")

    st.caption(
        "Emergency Intelligence & Resource Coordination"
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Command Center",
            "Emergency Reports",
            "Incidents",
            "Resources",
            "AI Activity",
            "Audit Trail",
        ]
    )

    st.divider()

    st.caption(f"Version {APP_VERSION}")

    st.warning(
        "Prototype system. AI recommendations "
        "require human verification."
    )


# ==================================================
# COMMAND CENTER
# ==================================================

if page == "Command Center":

    st.markdown(
        '<div class="header-title">'
        'Emergency Command Center'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="header-subtitle">'
        'Centralized emergency intelligence dashboard'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()

    stats = get_database_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Emergency Reports",
            stats["emergency_reports"],
        )

    with col2:
        st.metric(
            "Incidents",
            stats["incidents"],
        )

    with col3:
        st.metric(
            "Resources",
            stats["resources"],
        )

    with col4:
        st.metric(
            "AI Executions",
            stats["agent_executions"],
        )

    st.divider()

    st.subheader("Recent Emergency Reports")

    reports = get_emergency_reports(limit=5)

    if not reports:

        st.info(
            "No emergency reports have been submitted yet."
        )

    else:

        for report in reports:

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [2, 2, 1]
                )

                with col1:

                    st.markdown(
                        f"**{report['report_id']}**"
                    )

                    st.write(
                        report["description"]
                    )

                with col2:

                    st.write(
                        f"**Type:** "
                        f"{report['emergency_type']}"
                    )

                    st.write(
                        f"**Location:** "
                        f"{report['submitted_location'] or 'Not provided'}"
                    )

                with col3:

                    st.write(
                        "**Status**"
                    )

                    st.warning(
                        report["processing_status"]
                    )


# ==================================================
# EMERGENCY REPORTS
# ==================================================

elif page == "Emergency Reports":

    st.header("📥 Emergency Reporting")

    st.write(
        "Submit a simulated emergency report for "
        "RescueMind AI analysis."
    )

    st.warning(
        "This is a hackathon prototype. Do not use "
        "this application as a substitute for real "
        "emergency services."
    )

    st.divider()

    # ----------------------------------------------
    # REPORT FORM
    # ----------------------------------------------

    with st.form("emergency_report_form"):

        emergency_type = st.selectbox(
            "Emergency Type",
            EMERGENCY_TYPES,
        )

        description = st.text_area(
            "Emergency Description *",
            placeholder=(
                "Example: Heavy flooding is entering "
                "homes near the main road. Several "
                "people may be trapped."
            ),
            height=150,
        )

        location = st.text_input(
            "Location / Landmark *",
            placeholder=(
                "Example: Main Road near City Hospital"
            ),
        )

        st.markdown("### Optional Reporter Information")

        col1, col2 = st.columns(2)

        with col1:

            reporter_name = st.text_input(
                "Reporter Name"
            )

        with col2:

            reporter_contact = st.text_input(
                "Reporter Contact"
            )

        st.markdown("### Evidence")

        evidence_file = st.file_uploader(
            "Upload an emergency image",
            type=[
                "jpg",
                "jpeg",
                "png",
                "webp",
            ],
        )

        st.caption(
            "Images are treated as submitted evidence. "
            "AI interpretation will require verification."
        )

        submitted = st.form_submit_button(
            "🚨 Submit Emergency Report",
            use_container_width=True,
        )

        if submitted:

            # --------------------------------------
            # VALIDATION
            # --------------------------------------

            errors = []

            if not description.strip():

                errors.append(
                    "Emergency description is required."
                )

            if not location.strip():

                errors.append(
                    "Location or landmark is required."
                )

            if errors:

                for error in errors:

                    st.error(error)

            else:

                # ----------------------------------
                # EVIDENCE PROCESSING
                # ----------------------------------

                evidence_file_name = None
                evidence_file_type = None
                evidence_data = None

                if evidence_file:

                    evidence_file_name = (
                        evidence_file.name
                    )

                    evidence_file_type = (
                        evidence_file.type
                    )

                    evidence_data = (
                        evidence_file.getvalue()
                    )

                # ----------------------------------
                # SAVE REPORT
                # ----------------------------------

                report_id = save_emergency_report(
                    description=description.strip(),
                    emergency_type=emergency_type,
                    reported_time=datetime.now().isoformat(),
                    location=location.strip(),
                    reporter_name=(
                        reporter_name.strip()
                        if reporter_name
                        else None
                    ),
                    reporter_contact=(
                        reporter_contact.strip()
                        if reporter_contact
                        else None
                    ),
                    evidence_file_name=(
                        evidence_file_name
                    ),
                    evidence_file_type=(
                        evidence_file_type
                    ),
                    evidence_data=evidence_data,
                )

                st.success(
                    "Emergency report submitted successfully!"
                )

                st.markdown(
                    f"### Report ID: `{report_id}`"
                )

                st.info(
                    "Your report is now waiting for "
                    "AI analysis. No operational action "
                    "has been taken."
                )


# ==================================================
# INCIDENTS
# ==================================================

elif page == "Incidents":

    st.header("🚨 Incident Management")

    st.info(
        "Reports will become structured incidents "
        "after the AI analysis pipeline is implemented."
    )

    st.write("Incident workflow:")

    for status in INCIDENT_STATUSES:

        st.write(f"• {status}")


# ==================================================
# RESOURCES
# ==================================================

elif page == "Resources":

    st.header("🚑 Rescue Resources")

    st.info(
        "Simulated ambulances, rescue teams, boats, "
        "medical supplies, and other resources will "
        "be managed here."
    )


# ==================================================
# AI ACTIVITY
# ==================================================

elif page == "AI Activity":

    st.header("🤖 AI Agent Activity")

    st.info(
        "AI agent execution logging will appear here."
    )

    agents = [
        "Emergency Intake Agent",
        "Location Intelligence Agent",
        "Duplicate Detection Agent",
        "Severity Assessment Agent",
        "Resource Matching Agent",
        "Response Planning Agent",
        "Orchestrator",
    ]

    for agent in agents:

        st.write(f"• {agent}")


# ==================================================
# AUDIT TRAIL
# ==================================================

elif page == "Audit Trail":

    st.header("📜 Audit Trail")

    st.info(
        "System actions and human approvals will "
        "appear here."
    )
