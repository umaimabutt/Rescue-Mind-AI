import streamlit as st

from config import (
    APP_NAME,
    APP_VERSION,
    INCIDENT_STATUSES,
    EMERGENCY_TYPES,
)

from database import (
    initialize_database,
    get_database_stats,
    add_audit_log,
)


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------

initialize_database()


# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>

.main {
    background-color: #f5f7fa;
}

.block-container {
    padding-top: 2rem;
}

.metric-card {
    background-color: white;
    padding: 20px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
}

.header-title {
    font-size: 34px;
    font-weight: 700;
}

.header-subtitle {
    color: #6b7280;
    font-size: 16px;
}

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

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


# --------------------------------------------------
# COMMAND CENTER
# --------------------------------------------------

if page == "Command Center":

    st.markdown(
        '<div class="header-title">Emergency Command Center</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="header-subtitle">'
        'Centralized emergency intelligence dashboard'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    stats = get_database_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Emergency Reports",
            stats["emergency_reports"]
        )

    with col2:
        st.metric(
            "Incidents",
            stats["incidents"]
        )

    with col3:
        st.metric(
            "Resources",
            stats["resources"]
        )

    with col4:
        st.metric(
            "AI Executions",
            stats["agent_executions"]
        )

    st.divider()

    st.info(
        "The command center will become the main operational "
        "dashboard as the RescueMind AI agents are implemented."
    )

    st.subheader("System Architecture")

    st.markdown("""
    **Emergency Report**
    ↓  
    **Intake Agent**
    ↓  
    **Location Intelligence**
    ↓  
    **Duplicate Detection**
    ↓  
    **Severity Assessment**
    ↓  
    **Resource Matching**
    ↓  
    **Response Planning**
    ↓  
    **Human Approval**
    ↓  
    **Resource Assignment**
    """)


# --------------------------------------------------
# EMERGENCY REPORTS
# --------------------------------------------------

elif page == "Emergency Reports":

    st.header("📥 Emergency Reports")

    st.write(
        "Citizen emergency reports will be submitted "
        "through this module."
    )

    with st.form("emergency_report_form"):

        emergency_type = st.selectbox(
            "Emergency Type",
            EMERGENCY_TYPES
        )

        description = st.text_area(
            "Emergency Description",
            placeholder=(
                "Example: Water is rapidly entering houses "
                "near the main road..."
            )
        )

        location = st.text_input(
            "Reported Location",
            placeholder="Address or landmark"
        )

        submitted = st.form_submit_button(
            "Submit Emergency Report"
        )

        if submitted:

            if not description.strip():

                st.error(
                    "Please provide an emergency description."
                )

            else:

                st.success(
                    "Report validation successful. "
                    "AI intake processing will be added next."
                )


# --------------------------------------------------
# INCIDENTS
# --------------------------------------------------

elif page == "Incidents":

    st.header("🚨 Incident Management")

    st.info(
        "Incident creation, duplicate detection, "
        "severity assessment, and approval workflow "
        "will be implemented in the upcoming phases."
    )

    st.write("Available statuses:")

    for status in INCIDENT_STATUSES:
        st.write(f"• {status}")


# --------------------------------------------------
# RESOURCES
# --------------------------------------------------

elif page == "Resources":

    st.header("🚑 Rescue Resources")

    st.info(
        "Simulated ambulances, rescue teams, boats, "
        "medical supplies, and other resources will "
        "be managed here."
    )


# --------------------------------------------------
# AI ACTIVITY
# --------------------------------------------------

elif page == "AI Activity":

    st.header("🤖 AI Agent Activity")

    st.info(
        "Every AI agent execution will be recorded "
        "for explainability and auditing."
    )

    st.markdown("""
    Planned agents:

    - 🧾 Emergency Intake Agent
    - 📍 Location Intelligence Agent
    - 🔎 Duplicate Detection Agent
    - ⚠️ Severity Assessment Agent
    - 🚑 Resource Matching Agent
    - 📋 Response Planning Agent
    - 🧠 Orchestrator
    """)


# --------------------------------------------------
# AUDIT TRAIL
# --------------------------------------------------

elif page == "Audit Trail":

    st.header("📜 Audit Trail")

    st.info(
        "Human approvals, AI recommendations, "
        "status changes, and resource assignments "
        "will be recorded here."
    )
