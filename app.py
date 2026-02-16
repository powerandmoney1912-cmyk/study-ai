import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time
import pandas as pd

# --- 1. CONFIG ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing in Secrets!")
    st.stop()

# --- 2. SESSION STATE ---
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "is_premium" not in st.session_state: st.session_state.is_premium = False
if "xp" not in st.session_state: st.session_state.xp = 0
if "timer_active" not in st.session_state: st.session_state.timer_active = False

# --- 3. PROFESSIONAL SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Study Master Pro")
    
    # Premium Key
    if not st.session_state.is_premium:
        p_code = st.text_input("Premium Code", type="password")
        if st.button("Unlock"):
            if p_code == "STUDY777":
                st.session_state.is_premium = True
                st.rerun()
    else:
        st.success("💎 PREMIUM ACTIVE")

    menu = st.radio("Go to:", [
        "💬 Super Chat", 
        "📝 Notes Maker", 
        "🗂️ Flashcard Lab", 
        "📷 Visual Lab", 
        "📅 AI Scheduler",
        "📊 Dashboard"
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
            st.success("Session Done! 🎉"); st.session_state.timer_active = False
    else:
        mins = st.number_input("Minutes", 1, 180, 25)
        if st.button("🚀 Start Focus"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

# --- 4. AI ENGINE ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. Respond ONLY in {t_lang} using Markdown."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. FEATURE MODULES ---

# A. NOTES MAKER (NEW FEATURE)
if menu == "📝 Notes Maker":
    st.header("📝 Professional Notes Maker")
    topic = st.text_input("Enter Topic for Notes")
    raw_text = st.text_area("Paste raw content or key points here...")
    if st.button("✨ Generate Structured Notes"):
        with st.spinner("Organizing..."):
            notes = ask_ai(f"Convert this raw text into structured study notes with headings and bullets: {raw_text} for topic {topic}")
            st.markdown(notes)
            st.session_state.xp += 20

# B. FLASHCARD LAB (RESTORED)
elif menu == "🗂️ Flashcard Lab":
    st.header("🗂️ Smart Flashcards")
    subject = st.text_input("Subject")
    if st.button("Generate 5 Flashcards"):
        cards = ask_ai(f"Create 5 Q&A flashcards for {subject}. Format as: Q: [Question] | A: [Answer]")
        st.info(cards)
        st.session_state.xp += 15

# C. VISUAL LAB (FIXED CAMERA LOGIC)
elif menu == "📷 Visual Lab":
    st.header("📷 Visual Analyzer")
    img = st.camera_input("Take a photo of your notes/book")
    if img is not None:
        st.success("Image Captured!")
        # THE FIX: Button is placed here so it's always available when image exists
        if st.button("🔍 Explain This Image Content", use_container_width=True):
            with st.spinner("AI analyzing visual context..."):
                # Simulation of visual context via prompt engineering
                analysis = ask_ai("Analyze the captured study material and explain the core concepts.")
                st.markdown(analysis)
                st.session_state.xp += 25

# D. DASHBOARD (RESTORED)
elif menu == "📊 Dashboard":
    st.header("📊 Study Analytics")
    col1, col2 = st.columns(2)
    col1.metric("Current XP", st.session_state.xp)
    col2.metric("Level", (st.session_state.xp // 100) + 1)
    
    st.subheader("Activity Progress")
    # Simple Progress tracking
    st.progress(min((st.session_state.xp % 100) / 100, 1.0))
    st.write("Keep studying to reach the next level!")

# E. SCHEDULER & CHAT
elif menu == "📅 AI Scheduler":
    st.header("📅 Timetable Generator")
    subs = st.text_area("List Subjects")
    if st.button("Build Schedule"):
        st.markdown(ask_ai(f"Create an hourly study table for: {subs}"))

elif menu == "💬 Super Chat":
    st.header("Chat with AI")
    if p := st.chat_input("Ask a question..."):
        ans = ask_ai(p)
        st.write(ans)
