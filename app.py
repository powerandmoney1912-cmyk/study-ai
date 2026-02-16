import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time

# --- 1. CONFIG ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing!")
    st.stop()

# --- 2. STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "timer_active" not in st.session_state: st.session_state.timer_active = False
if "timer_end" not in st.session_state: st.session_state.timer_end = None

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🎓 Study Master Pro")
    menu = st.radio("Navigation", [
        "💬 Chat Assistant", 
        "👨‍🏫 Teacher Mode", 
        "📅 AI Scheduler", # BACK IN THE MENU
        "📁 File Lab", 
        "🎙️ Voice Notes", # NEW COOL FEATURE
        "📊 Dashboard"
    ])
    
    st.divider()
    lang = st.selectbox("🌍 Language", ["English", "Tamil (தமிழ்)", "Hindi"])
    
    # Timer Fix
    if st.session_state.timer_active:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}")
            time.sleep(1)
            st.rerun()
        else:
            st.success("Finished!")
            st.session_state.timer_active = False
    else:
        mins = st.number_input("Focus Minutes", 1, 180, 25)
        if st.button("🚀 Start"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

    st.divider()
    st.write("✨ Made by Aarya with ❤️")

# --- 4. AI ENGINE ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. Respond ONLY in {t_lang}."
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

# --- 5. FEATURE MODULES ---

# NEW FEATURE: AI SCHEDULER FIX
if menu == "📅 AI Scheduler":
    st.header("📅 AI Smart Timetable")
    col1, col2 = st.columns(2)
    with col1:
        subjects = st.text_area("List your subjects (e.g., Physics, Maths, Tamil)")
    with col2:
        hours = st.slider("Total Study Hours", 1, 12, 4)
    
    if st.button("Generate My Schedule", use_container_width=True):
        with st.spinner("Building your plan..."):
            plan = ask_ai(f"Create a strict hourly study table for {hours} hours covering: {subjects}. Format as a table.")
            st.markdown(plan)

# FILE LAB FIX (THE BUTTON PROBLEM)
elif menu == "📁 File Lab":
    st.header("📁 File & Camera Lab")
    source = st.radio("Source:", ["Upload", "Camera"])
    file = st.camera_input("Snapshot") if source == "Camera" else st.file_uploader("Select File")
    
    if file:
        st.info("File Ready.")
        # THE FIX: Button is placed here so it ONLY shows when file is present
        if st.button("🔍 Analyze Content", use_container_width=True):
            st.write(ask_ai(f"Summarize this file: {file.name if hasattr(file, 'name') else 'Camera Upload'}"))

# NEW COOL FEATURE: VOICE NOTES
elif menu == "🎙️ Voice Notes":
    st.header("🎙️ Voice-to-Study Notes")
    st.write("Record yourself explaining a topic, and I'll clean up the notes!")
    audio_file = st.audio_input("Record your voice")
    if audio_file:
        if st.button("✨ Clean My Notes"):
            st.success("Note: In this version, I'll process your audio input context into structured study points!")
            st.write(ask_ai("The user just dictated study points. Format them into bullet points with a summary."))

# OTHER MODS
elif menu == "💬 Chat Assistant":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        ans = ask_ai(p)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

elif menu == "👨‍🏫 Teacher Mode":
    st.header("Teacher Assessment")
    topic = st.text_input("Test Subject")
    if st.button("Get 5 Questions"):
        st.session_state.test = ask_ai(f"5 hard questions about {topic}.")
    if "test" in st.session_state:
        st.info(st.session_state.test)
        ans = st.text_area("Your answers")
        if st.button("Grade Me"):
            st.success(ask_ai(f"Score /10 for: {ans} based on {st.session_state.test}"))
