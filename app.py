import streamlit as st

st.set_page_config(
    page_title="RescueMind AI",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 RescueMind AI")
st.subheader("AI-Powered Emergency Intelligence & Resource Coordination")

st.info(
    "Hackathon Prototype — All emergency data and recommendations "
    "are simulated and require human verification."
)

st.success("RescueMind AI foundation is running successfully!")

st.write("### System Status")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Incidents", "0")

with col2:
    st.metric("Urgent", "0")

with col3:
    st.metric("Resources", "0")

with col4:
    st.metric("Pending Review", "0")
