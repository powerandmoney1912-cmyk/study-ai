import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import json

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

# Connect to Services
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Missing Secrets! Add GROQ_API_KEY and [supabase] keys to Streamlit Settings.")
    st.stop()

# --- 2. SESSION STATE ---
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE HELPERS ---
def get_usage():
    try:
        day_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user_uuid).gte("created_at", day_ago).execute()
        return res.count if res.count else 0
    except: return 0

def log(role, content):
    try: supabase.table("history").insert({"user_id": st.session_state.user_uuid, "role": role, "content": str(content)}).execute()
    except: pass

# --- 4. SIDEBAR ---
st.sidebar.title("🎓 Study Master Pro")

# Premium Redemption
if not st.session_state.is_premium:
    with st.sidebar.expander("🔑 REDEEM CODE"):
        c = st.text_input("Code", type="password")
        if st.button("Unlock 250 Chats") and c == "STUDY777":
            st.session_state.is_premium = True
            st.rerun()
else:
    st.sidebar.success("💎 Premium Active")

# Progress Tracker
usage = get_usage()
limit = 250 if st.session_state.is_premium else 50
st.sidebar.write(f"Daily Limit: {usage}/{limit}")
st.sidebar.progress(min(usage/limit, 1.0))

menu = st.sidebar.radio("Navigation", ["Chat", "Teacher Mode", "Quiz Zone", "AI Scheduler", "History"])

# --- 5. AI ENGINE ---
def ask_ai(prompt, sys="You are a study expert."):
    if usage >= limit: return "OVER_LIMIT"
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 6. APP MODULES ---

if menu == "Chat":
    st.header("💬 Study Chat")
    p = st.chat_input("Ask a question...")
    if p:
        st.chat_message("user").write(p)
        ans = ask_ai(p)
        if ans == "OVER_LIMIT": st.error("Limit reached!")
        else:
            st.chat_message("assistant").write(ans)
            log("user", p); log("assistant", ans)

elif menu == "Teacher Mode":
    st.header("👨‍🏫 Teacher Mode (Grading)")
    topic = st.text_input("Topic to be tested on:")
    if topic and st.button("Generate Test"):
        st.session_state.test = ask_ai(f"Give 5 questions about {topic}. No answers.")
    
    if "test" in st.session_state:
        st.info(st.session_state.test)
        ans_box = st.text_area("Your Answers:")
        if st.button("Grade Me"):
            grade = ask_ai(f"Grade these answers for the test: {st.session_state.test}. User answers: {ans_box}. Give marks out of 10.")
            st.success(grade)
            log("teacher", grade)

elif menu == "Quiz Zone":
    st.header("📝 Quiz Zone")
    t = st.text_input("Quiz topic:")
    if t and st.button("Generate Quiz"):
        st.write(ask_ai(f"Create a 5-question MCQ quiz on {t} with answers at the bottom."))

elif menu == "AI Scheduler":
    st.header("📅 AI Study Scheduler")
    col1, col2 = st.columns(2)
    with col1:
        subjects = st.text_area("List your subjects (comma separated):")
        hours = st.slider("Daily study hours:", 1, 12, 4)
    with col2:
        goal = st.selectbox("Your Goal:", ["Exam Prep", "General Learning", "Homework Help"])
        
    if st.button("Generate Full Timetable"):
        with st.spinner("Preparing your schedule..."):
            sched_prompt = f"Create a detailed hourly study timetable for {hours} hours a day for these subjects: {subjects}. Goal: {goal}. Format it as a clean table."
            timetable = ask_ai(sched_prompt)
            st.markdown(timetable)
            # Save to Supabase
            supabase.table("schedules").insert({"user_id": st.session_state.user_uuid, "plan_name": goal, "timetable": {"content": timetable}}).execute()

elif menu == "History":
    st.header("📜 History")
    h = supabase.table("history").select("*").eq("user_id", st.session_state.user_uuid).order("created_at", desc=True).limit(10).execute()
    for item in h.data:
        st.write(f"**{item['role']}**: {item['content'][:150]}...")
