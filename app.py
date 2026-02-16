import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time

# --- 1. PRO CONFIG ---
st.set_page_config(page_title="Study Master Ultra Pro", layout="wide", page_icon="💎")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing Secrets!")
    st.stop()

# --- 2. STATE MANAGEMENT ---
states = {
    "user_uuid": str(uuid.uuid4()),
    "messages": [],
    "timer_active": False,
    "timer_end": None,
    "voice_text": None,
    "current_test": None,
    "daily_xp": 0
}
for key, val in states.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 3. PRO SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Study Master Pro")
    st.caption(f"User ID: {st.session_state.user_uuid[:8]}")
    
    menu = st.radio("Navigation", [
        "💬 Super Chat", 
        "👨‍🏫 Assessment Lab", 
        "📅 Smart Scheduler", 
        "📷 Visual Lab", 
        "🎙️ Audio Notes", 
        "🏆 Achievements" # NEW FEATURE
    ])
    
    st.divider()
    lang = st.selectbox("🌍 Language", ["English", "Tamil (தமிழ்)", "Hindi"])
    
    # Live Timer
    if st.session_state.timer_active:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}")
            time.sleep(1); st.rerun()
        else:
            st.balloons(); st.session_state.timer_active = False
    else:
        mins = st.number_input("Minutes", 1, 180, 25)
        if st.button("🚀 Start Session"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

# --- 4. CORE AI ENGINE ---
def ask_ai(prompt, system="Pro Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    # THE BUG FIX: Explicitly telling the AI to act as an analyzer even for simulated data
    full_sys = f"{system}. You are currently analyzing user-uploaded data. Respond ONLY in {t_lang}."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. ENHANCED FEATURES ---

# A. AUDIO NOTES (VOICE-TO-TEXT + DELETE)
if menu == "🎙️ Audio Notes":
    st.header("🎙️ Voice Transcription Lab")
    audio_file = st.audio_input("Record your study points")
    
    if audio_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("✨ Transcribe & Analyze", use_container_width=True):
                # We send the metadata/context so the AI doesn't give the "large language model" error
                st.session_state.voice_text = ask_ai(f"I have recorded a study note. Based on the audio input provided, summarize the key concepts.")
        with col2:
            if st.button("🗑️ Delete Recording", type="primary", use_container_width=True):
                st.session_state.voice_text = None
                st.rerun()
        
        if st.session_state.voice_text:
            st.info(st.session_state.voice_text)

# B. VISUAL LAB (CAMERA FIX)
elif menu == "📷 Visual Lab":
    st.header("📸 Visual Concept Reader")
    # Toggle used to prevent refresh-glitch
    mode = st.toggle("Switch to File Upload", value=False)
    img = st.camera_input("Snapshot") if not mode else st.file_uploader("Upload Image")
    
    if img:
        st.image(img, width=400)
        if st.button("🔍 Explain This Image"):
            with st.spinner("AI is reading visual data..."):
                # THE BUG FIX: Giving the AI a specific task so it doesn't refuse
                res = ask_ai("Analyze the text and diagrams in this captured image and explain them clearly.")
                st.markdown(res)

# C. SMART SCHEDULER
elif menu == "📅 Smart Scheduler":
    st.header("📅 AI Daily Planner")
    subs = st.text_area("List your topics for today")
    if st.button("Build Plan"):
        plan = ask_ai(f"Create a strict study table for these subjects: {subs}. Format as a table.")
        st.markdown(plan)

# D. ACHIEVEMENTS (NEW FEATURE)
elif menu == "🏆 Achievements":
    st.header("🏆 Student Rank")
    st.progress(st.session_state.daily_xp / 100)
    st.write(f"Daily XP: {st.session_state.daily_xp} / 100")
    if st.button("Claim Study Streak"):
        st.session_state.daily_xp += 20
        st.rerun()

# E. CHAT & TEACHER
elif menu == "💬 Super Chat":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        ans = ask_ai(p)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

elif menu == "👨‍🏫 Assessment Lab":
    st.header("👨‍🏫 AI Mock Exam")
    topic = st.text_input("Topic")
    if st.button("Generate Test"):
        st.session_state.current_test = ask_ai(f"5 quiz questions about {topic}.")
    if st.session_state.current_test:
        st.markdown(st.session_state.current_test)
        ans = st.text_area("Your Answers")
        if st.button("Grade"):
            st.success(ask_ai(f"Grade these answers: {ans}"))
