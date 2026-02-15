import streamlit as st
import google.generativeai as genai

# --- 1. MODERN UI SETUP ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="centered")

# Custom CSS to make the home page look cool
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stChatMessage { border-radius: 20px; border: 1px solid #30363d; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. SECURE API CONNECTION ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Using the 2026 stable alias
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("Missing API Key in Secrets!")
    st.stop()

# --- 3. CHAT HISTORY (The "Memory") ---
# We initialize a session that stays active until the page is closed
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# --- 4. COOL HOME PAGE HEADER ---
st.title("🚀 Study Master Pro")
st.info("I now have 'Persistent Memory.' You can ask me follow-up questions!")

# --- 5. DISPLAY HISTORY ---
# This loop ensures your old messages stay on the screen after you type
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 6. CHAT INPUT & INTERACTION ---
if prompt := st.chat_input("What are we studying today?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            # We send messages through the 'session' so it remembers context
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")

# --- 7. SIDEBAR FEATURES ---
with st.sidebar:
    st.title("🎓 Dashboard")
    if st.button("🗑️ Clear Conversation"):
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()
