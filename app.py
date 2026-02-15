import streamlit as st
import google.generativeai as genai

# 1. ENHANCED PAGE CONFIG (The "Cool" factor)
st.set_page_config(
    page_title="Study Master Pro AI",
    page_icon="🧠",
    layout="centered"
)

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. API SETUP
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("API Key missing!")
    st.stop()

# 3. CHAT HISTORY LOGIC (The "Memory")
# This ensures the AI remembers the conversation
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])

# 4. HEADER UI
st.title("🚀 Study Master Pro")
st.markdown("---")

# 5. DISPLAY MESSAGES FROM HISTORY
# We loop through the internal chat history to show previous bubbles
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# 6. CHAT INPUT & AUTOMATIC MEMORY
if prompt := st.chat_input("Ask me a study question..."):
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get AI response using the session (so it remembers context)
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")

# 7. SIDEBAR FEATURES
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3413/3413535.png", width=100)
    st.title("Study Dashboard")
    st.info("Everything you ask here is saved in this session's history.")
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_session = model.start_chat(history=[])
        st.rerun()
