import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from gtts import gTTS
import os
import base64

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="Study Master Pro", page_icon="🧠", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: #6e7681; font-size: 14px; padding: 10px; background: #0e1117; }
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 2px 5px; border-radius: 5px; }
    </style>
    <div class="footer">Made with ❤️ by Aarya Venkat, an average 14-year-old boy</div>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR & PREMIUM LOGIC ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    access_code = st.text_input("Enter Premium Code:", type="password")
    is_premium = (access_code == "STUDY2026")
    
    if is_premium:
        st.success("✨ Premium Unlocked!")
        model_name = 'gemini-2.5-flash'
    else:
        st.info("Free Version Active")
        model_name = 'gemini-2.5-flash-lite'
    
    st.divider()
    # FEATURE C: PDF UPLOADER
    st.subheader("📁 Upload Notes (PDF)")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_session = None
        st.rerun()

# --- 3. INITIALIZE AI ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(model_name)

if "chat_session" not in st.session_state or st.session_state.chat_session is None:
    st.session_state.chat_session = model.start_chat(history=[])

# --- 4. MAIN UI ---
badge = " <span class='premium-badge'>PREMIUM</span>" if is_premium else ""
st.markdown(f"<h1>🚀 Study Master Pro{badge}</h1>", unsafe_allow_html=True)

# Handle PDF Content
if uploaded_file is not None:
    reader = PdfReader(uploaded_file)
    pdf_text = "".join([page.extract_text() for page in reader.pages])
    st.success("PDF Content Loaded! You can now ask questions about it.")
    # Add PDF content to history silently
    if "pdf_added" not in st.session_state:
        st.session_state.chat_session.send_message(f"System: The user has uploaded a document with this content: {pdf_text[:2000]}. Please use this for context.")
        st.session_state.pdf_added = True

# Display Chat
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# --- 5. CHAT INPUT & FEATURES A & B ---
if prompt := st.chat_input("Ask anything..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        st.markdown(response.text)
        
        # FEATURE B: VOICE (Text-to-Speech)
        tts = gTTS(text=response.text[:300], lang='en') # Limit to first 300 chars for speed
        tts.save("response.mp3")
        audio_file = open("response.mp3", "rb")
        audio_bytes = audio_file.read()
        st.audio(audio_bytes, format="audio/mp3")

# FEATURE A: QUIZ MODE BUTTON
st.divider()
if st.button("📝 Generate Quick Quiz"):
    with st.spinner("Creating a quiz based on our chat..."):
        quiz_prompt = "Based on our conversation so far, generate 3 multiple choice questions to test my knowledge. Provide the answers at the end."
        response = st.session_state.chat_session.send_message(quiz_prompt)
        st.info(response.text)
