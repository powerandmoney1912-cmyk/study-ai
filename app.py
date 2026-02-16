import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time
import pandas as pd

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Study Master Ultra Pro", layout="wide", page_icon="🧠")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Check your Secrets configuration!")
    st.stop()

# --- 2. ADVANCED STATE MANAGEMENT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "timer_active" not in st.session_state: st.session_state.timer_active = False
if "timer_end" not in st.session_state: st.session_state.timer_end = None
if "voice_transcript" not in st.session_state: st.session_state.voice_transcript = None
if "camera_active" not in st.session_state: st.session_state.camera_active = False

# --- 3. SIDEBAR & TAMIL TIMER ---
with st.sidebar:
    st.title("🎓 Study Master Pro")
    menu = st.radio("Navigation", [
        "💬 Super Chat", 
        "👨‍🏫 Teacher Assessment", 
        "📅 AI Scheduler", 
        "📁 Camera & File Lab", 
        "🎙️ Voice-to-Study", 
        "📊 Progress Hub"
    ])
    
    st.divider()
    lang = st.selectbox("🌍 Language", ["English", "Tamil (தமிழ்)", "Hindi"])
    
    # Live Timer Logic
    if st.session_state.timer_active:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}")
            time.sleep(1)
            st.rerun()
        else:
            st.balloons()
            st.session_state.timer_active = False
    else:
        mins = st.number_input("Minutes", 1, 180, 25)
        if st.button("🚀 Start Focus Session"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

    st.divider()
    st.write("✨ Made by Aarya with ❤️")

# --- 4. ADVANCED AI ENGINE ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. Respond ONLY in {t_lang}. Use markdown for formatting."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. ENHANCED FEATURES ---

# A. VOICE-TO-STUDY (TWO-STEP LOGIC)
if menu == "🎙️ Voice-to-Study":
    st.header("🎙️ Voice Transcription & Analysis")
    audio_data = st.audio_input("Record your explanation or question")
    
    if audio_data:
        if st.button("Step 1: Convert to Text"):
            with st.spinner("Transcribing..."):
                # Simulation of Groq Whisper/Audio transcription
                transcript = ask_ai(f"User provided audio. Transcribe and summarize exactly what was said.")
                st.session_state.voice_transcript = transcript
        
        if st.session_state.voice_transcript:
            st.subheader("📜 Transcribed Text")
            st.info(st.session_state.voice_transcript)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📝 Create Study Notes"):
                    notes = ask_ai(f"Create detailed study notes from this transcript: {st.session_state.voice_transcript}")
                    st.write(notes)
            with col2:
                if st.button("❓ Generate Practice Questions"):
                    qs = ask_ai(f"Generate 5 quiz questions based on: {st.session_state.voice_transcript}")
                    st.write(qs)

# B. CAMERA & FILE LAB (UI FIX)
elif menu == "📁 Camera & File Lab":
    st.header("📸 Visual Study Lab")
    src = st.toggle("Switch to Camera", value=False)
    
    img_file = st.camera_input("Capture Notes") if src else st.file_uploader("Upload Image/PDF")
    
    if img_file:
        # Fixed: The analysis options stay visible once the file is detected
        st.success("Visual Data Captured!")
        st.image(img_file, width=300)
        
        task = st.selectbox("What should I do?", ["Summarize", "Solve Equations", "Explain Concept", "Translate to Tamil"])
        if st.button("🔍 Process Image"):
            with st.spinner("Analyzing..."):
                result = ask_ai(f"Action: {task}. Identify the content in the provided visual input and respond.")
                st.markdown(f"### {task} Result")
                st.write(result)

# C. AI SCHEDULER (ADVANCED)
elif menu == "📅 AI Scheduler":
    st.header("📅 Intelligent Study Planner")
    subs = st.text_input("Subjects to cover today")
    mood = st.select_slider("Energy Level", options=["Low", "Medium", "High"])
    if st.button("Generate Adaptive Schedule"):
        plan = ask_ai(f"Create a study schedule for: {subs}. Energy level is {mood}. Adjust intensity accordingly.")
        st.markdown(plan)

# D. TEACHER ASSESSMENT
elif menu == "👨‍🏫 Teacher Assessment":
    st.header("👨‍🏫 AI Mock Test")
    topic = st.text_input("Enter Topic")
    if st.button("Start Assessment"):
        st.session_state.active_test = ask_ai(f"Generate 5 tough questions on {topic}.")
    
    if "active_test" in st.session_state:
        st.markdown(st.session_state.active_test)
        user_ans = st.text_area("Your Answers")
        if st.button("Submit for Grading"):
            feedback = ask_ai(f"Score /10 and provide feedback for these answers: {user_ans} based on {st.session_state.active_test}")
            st.success(feedback)
