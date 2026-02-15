import streamlit as st
import google.generativeai as genai

# --- 1. COOL UI CONFIG ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="wide")

# Custom CSS for that "Pro" look
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stChatMessage { border-radius: 20px; padding: 15px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API & MEMORY SETUP ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# This is the "Chat History" brain
if "chat_history" not in st.session_state:
    # Starting a session that saves history automatically
    st.session_state.chat_history = model.start_chat(history=[])

# --- 3. SIDEBAR (NEW FEATURES) ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    st.divider()
    st.info("I remember our conversation. You can ask follow-up questions!")
    
    # Feature: Clear Chat button
    if st.button("🗑️ Reset Conversation"):
        st.session_state.chat_history = model.start_chat(history=[])
        st.rerun()

# --- 4. MAIN INTERFACE ---
st.title("🚀 Study Master Pro")
st.caption("Advanced Academic Assistant with Persistent Memory")

# Display the history on every refresh
for message in st.session_state.chat_history.history:
    # Google uses "model", Streamlit uses "assistant"
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 5. CHAT INPUT ---
if prompt := st.chat_input("What are we studying today?"):
    # Display user message instantly
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get response using the SESSION (not just the model)
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_history.send_message(prompt)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")
