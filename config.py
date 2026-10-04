import os
import streamlit as st


APP_NAME = "RescueMind AI"
APP_VERSION = "1.0.0"

DATABASE_FILE = "rescuemind.db"

INCIDENT_STATUSES = [
    "Pending",
    "Under Review",
    "Approved",
    "Assigned",
    "In Progress",
    "Resolved",
]

EMERGENCY_TYPES = [
    "Flood",
    "Earthquake",
    "Fire",
    "Road Accident",
    "Medical Emergency",
    "Other",
]

SEVERITY_LEVELS = [
    "Critical",
    "High",
    "Medium",
    "Low",
    "Unknown",
]


def get_groq_api_key():
    """
    Safely retrieve the Groq API key from Streamlit Secrets.
    Falls back to environment variables for local development.
    """

    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    return os.getenv("GROQ_API_KEY")
