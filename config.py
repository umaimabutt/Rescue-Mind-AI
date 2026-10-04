import os
import streamlit as st


APP_NAME = "RescueMind AI"
APP_VERSION = "2.0.0"

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


# Current Groq text models
GROQ_TEXT_MODEL = "openai/gpt-oss-20b"
GROQ_FALLBACK_MODEL = "openai/gpt-oss-120b"

# Groq Whisper model
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"


def get_groq_api_key():

    # First check Streamlit Secrets
    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass

    # Then check environment variable
    return os.getenv("GROQ_API_KEY")
