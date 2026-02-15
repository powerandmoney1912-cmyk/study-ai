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
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: #6e7681; font-size: 14px; padding: 10px; background: #0e1117; z-index: 100; }
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 2px 5px; border-radius: 5px; }
    </style>
    <div class="footer">Made with ❤️ by Aarya Venkat, an average 14-year-old boy</div>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("🎓 Study Dashboard")
    access_code = st.text_input("Enter Premium Code:", type="password")
    is_premium = (access_code == "STUDY2026")
    model_name = 'gemini-2.5-flash' if is_premium else 'gemini-2.5-flash-lite'
    
    st.divider()
    st.subheader("📁 Upload Notes (PDF)")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf")
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_session = None
        st.session_state.pdf_added = False
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
if uploaded_file is not None and "pdf_added" not in st.session_state:
    reader = PdfReader(uploaded_file)
    pdf_text = "".join([page.extract_text() for page in reader.pages])
    st.session_state.chat_session.send_message(f"SYSTEM: User uploaded a PDF. Content: {pdf_text[:2000]}. Use this for future context.")
    st.session_state.pdf_added = True
    st.success("PDF Loaded! Ask me anything about it.")

# Display Chat History
for message in st.session_state.chat_session.history:
    # Filter out the "System" messages so the user doesn't see background instructions
    if not message.parts[0].text.startswith("SYSTEM:"):
        role = "assistant" if message.role == "model" else "user"
        with st.chat_message(role):
            st.markdown(message.parts[0].text)

# --- 5. CHAT INPUT & VOICE ---
if prompt := st.chat_input("Ask anything..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        response = st.session_state.chat_session.send_message(prompt)
        st.markdown(response.text)
        
        # Audio feature
        tts = gTTS(text=response.text[:300], lang='en')
        tts.save("response.mp3")
        with open("response.mp3", "rb") as f:
            st.audio(f.read(), format="audio/mp3")

# --- 6. QUIZ MODE (HIDDEN ANSWERS) ---
st.divider()
if st.button("📝 Generate Quick Quiz"):
    with st.spinner("Preparing your questions..."):
        # We tell the AI NOT to show answers yet
        quiz_instruction = (
            "SYSTEM: Generate 3 multiple choice questions based on our chat. "
            "IMPORTANT: Do NOT show the answers or the answer key now. "
            "Simply state: 'I have the answers ready. Type \"answer\" when you want to see them.' "
            "Wait for the user to type 'answer' specifically before revealing them."
        )
        response = st.session_state.chat_session.send_message(quiz_instruction)
        # Display the quiz on the screen
        st.info(response.text)
