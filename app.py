import streamlit as st
import google.generativeai as genai
import time

# --- 1. PAGE & STYLE CONFIG ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API INITIALIZATION ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ GOOGLE_API_KEY not found in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# LINE 25: This is the specific fix for your Daily Quota (429) error
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 3. PERSISTENT CHAT HISTORY ---
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    if st.button("🗑️ Clear History"):
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()

# --- 5. MAIN INTERFACE ---
st.title("🚀 Study Master Pro")
st.caption("AI-Powered Academic Assistant | v2.1")

for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 6. USER INPUT ---
if prompt := st.chat_input("What are we learning today?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
        except Exception as e:
            if "429" in str(e):
                st.error("⏳ Daily limit reached! Even the Lite model has a ceiling. Try again in a bit.")
            else:
                st.error(f"⚠️ Technical Glitch: {e}")
