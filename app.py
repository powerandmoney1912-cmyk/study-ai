import streamlit as st
import google.generativeai as genai
import time

# --- 1. PAGE & STYLE CONFIG ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="wide")

# Custom CSS for Dark Theme and Footer
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; border: 1px solid #30363d; }
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 5px; border-radius: 5px; }
    
    /* Custom Footer Style */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #0e1117;
        color: #6e7681;
        text-align: center;
        padding: 10px;
        font-size: 14px;
        border-top: 1px solid #30363d;
    }
    </style>
    <div class="footer">
        Made with ❤️ by Aarya Venkat, an average 14-year-old boy
    </div>
""", unsafe_allow_html=True)

# --- 2. PREMIUM & SIDEBAR ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    access_code = st.text_input("Enter Premium Code:", type="password")
    
    if access_code == "STUDY2026":
        is_premium = True
        st.success("✨ Premium Unlocked!")
        selected_model = 'gemini-2.5-flash'  # Smarter Model
    else:
        is_premium = False
        selected_model = 'gemini-2.5-flash-lite' # High Quota Model
    
    st.divider()
    st.caption("Developed by Aarya Venkat")
    if st.button("🗑️ Clear History"):
        st.session_state.chat_session = None
        st.rerun()

# --- 3. API INITIALIZATION ---
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ API Key missing in Secrets!")
    st.stop()

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(selected_model)

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# --- 4. MAIN INTERFACE ---
title_suffix = " <span class='premium-badge'>PREMIUM</span>" if is_premium else ""
st.markdown(f"<h1>🚀 Study Master Pro{title_suffix}</h1>", unsafe_allow_html=True)
st.caption(f"Running on: {selected_model}")

# Display history
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 5. CHAT INPUT ---
if prompt := st.chat_input("What are we learning today?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
        except Exception as e:
            if "429" in str(e):
                st.error("⏳ Limit reached! Try the Premium code or wait a few minutes.")
            else:
                st.error(f"⚠️ Error: {e}")
