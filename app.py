import streamlit as st
import google.generativeai as genai
import time

# --- 1. PAGE & STYLE CONFIG ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="wide")

# Modern Dark UI Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; border: 1px solid #30363d; }
    .stChatInputContainer { padding-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API INITIALIZATION ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ GOOGLE_API_KEY not found in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Use the 2026 stable model alias
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. PERSISTENT CHAT HISTORY (Memory) ---
# This initializes the 'brain' of the chat
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# --- 4. SIDEBAR DASHBOARD ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    st.markdown("---")
    st.info("I remember our conversation! Ask follow-up questions about anything we discussed.")
    
    if st.button("🗑️ Clear History"):
        # This resets the memory without crashing the app
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()

# --- 5. CHAT INTERFACE ---
st.title("🚀 Study Master Pro")
st.caption("AI-Powered Academic Assistant | v2.0")

# Display every message stored in the history
for message in st.session_state.chat_session.history:
    # Gemini uses 'model', Streamlit uses 'assistant'
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 6. USER INPUT & ERROR HANDLING ---
if prompt := st.chat_input("What are we learning today?"):
    # Show user message instantly
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate AI response
    with st.chat_message("assistant"):
        try:
            # We use send_message so it includes the history automatically
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            
        except Exception as e:
            # Catch the 429 "Too Many Requests" error specifically
            if "429" in str(e):
                st.error("⏳ You're moving a bit fast! Please wait 60 seconds for the free limit to reset.")
            else:
                st.error(f"⚠️ Technical Glitch: {e}")
