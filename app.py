import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time
import pandas as pd

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing in Secrets!")
    st.stop()

# --- 2. STATE MANAGEMENT ---
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "timer_active" not in st.session_state: st.session_state.timer_active = False
if "timer_end" not in st.session_state: st.session_state.timer_end = None

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🎓 Study Master Pro")
    # THE FULL MENU YOU REQUESTED
    menu = st.radio("Navigation", [
        "💬 Chat Assistant", 
        "👨‍🏫 Teacher Mode", 
        "📅 AI Scheduler", 
        "📝 Flashcard Lab", 
        "📁 File Lab", 
        "📊 Dashboard"
    ])
    
    st.divider()
    # TAMIL ADDED HERE
    lang = st.selectbox("🌍 Language", ["English", "Tamil (தமிழ்)", "Hindi", "Spanish", "French"])
    
    st.divider()
    st.subheader("⏱️ Focus Timer")
    if not st.session_state.timer_active:
        mins = st.number_input("Minutes", 1, 180, 25)
        if st.button("🚀 Start"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()
    else:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}") # Counting fix
            if st.button("🛑 Stop"):
                st.session_state.timer_active = False
                st.session_state.timer_end = None
                st.rerun()
            time.sleep(1)
            st.rerun()
        else:
            st.success("Finished! 🎉")
            st.session_state.timer_active = False

    st.divider()
    st.write("✨ **Made by Aarya**")
    st.write("❤️ *Made with love*")

# --- 4. AI ENGINE (TAMIL READY) ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. You MUST respond ONLY in {t_lang}."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. APP FEATURES ---

if menu == "💬 Chat Assistant":
    st.header("Study Chat")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": p})
        ans = ask_ai(p)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

elif menu == "👨‍🏫 Teacher Mode":
    st.header("AI Teacher Assessment")
    topic = st.text_input("Test Topic")
    if st.button("Get Questions"):
        st.session_state.test = ask_ai(f"Give 5 questions about {topic}.")
    if "test" in st.session_state:
        st.info(st.session_state.test)
        ans = st.text_area("Your answers:")
        if st.button("Submit"):
            st.success(ask_ai(f"Grade these: {ans} for: {st.session_state.test}"))

elif menu == "📅 AI Scheduler":
    st.header("Timetable Generator")
    subs = st.text_input("Subjects")
    if st.button("Generate"):
        st.markdown(ask_ai(f"Create a study schedule for: {subs}"))

elif menu == "📝 Flashcard Lab":
    st.header("Flashcards")
    ft = st.text_input("Flashcard Topic")
    if st.button("Generate Cards"):
        st.write(ask_ai(f"Create 5 flashcards for {ft}."))

elif menu == "📁 File Lab":
    st.header("File Summary")
    up = st.file_uploader("Upload File", type=['pdf','png','jpg'])
    if up: st.write(ask_ai(f"Summarize {up.name}"))

elif menu == "📊 Dashboard":
    st.header("Your Progress")
    st.write("Performance data loading from Supabase...")
