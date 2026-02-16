import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

# Initialize Supabase and Groq
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# --- 2. SESSION STATE ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4()) # Temporary ID for demo; replace with Auth
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE LOGIC (History & Limits) ---
def get_usage_count():
    """Checks history table for messages sent in the last 24h"""
    yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
    res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user_id).gte("created_at", yesterday).execute()
    return res.count if res.count else 0

def save_chat(role, content):
    supabase.table("history").insert({"user_id": st.session_state.user_id, "role": role, "content": content}).execute()

# --- 4. SIDEBAR (Premium & Navigation) ---
st.sidebar.title("🎓 Study Master Pro")

# Premium Redemption
if not st.session_state.is_premium:
    with st.sidebar.expander("🔑 REDEEM PREMIUM"):
        code = st.text_input("Enter Code", type="password")
        if st.button("Activate"):
            if code == "STUDY777": # Your specific code
                st.session_state.is_premium = True
                st.success("Premium Activated!")
                st.rerun()
            else:
                st.error("Invalid Code")
else:
    st.sidebar.success("💎 Premium Active")

# Usage Meter
usage = get_usage_count()
limit = 250 if st.session_state.is_premium else 50
st.sidebar.write(f"Daily Usage: **{usage} / {limit}**")
st.sidebar.progress(min(usage/limit, 1.0))

menu = st.sidebar.radio("Navigation", ["Chat", "Teacher Mode", "Quiz Mode", "History"])

# --- 5. APP FEATURES ---

# A. Normal Chat
if menu == "Chat":
    st.title("💬 AI Study Chat")
    if usage >= limit:
        st.warning("Daily limit reached! Enter a premium code for 250 chats.")
    else:
        prompt = st.chat_input("Ask a study question...")
        if prompt:
            st.chat_message("user").write(prompt)
            resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
            reply = resp.choices[0].message.content
            st.chat_message("assistant").write(reply)
            save_chat("user", prompt)
            save_chat("assistant", reply)

# B. Teacher Mode (Test without answers)
elif menu == "Teacher Mode":
    st.title("👨‍🏫 Teacher Mode: Assessment")
    topic = st.text_input("What topic should the teacher test you on?")
    if topic and st.button("Start Test"):
        prompt = f"Act as a strict teacher. Give me a 5-question test about {topic}. DO NOT provide the answers. Just the questions."
        test = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
        st.session_state.current_test = test.choices[0].message.content
    
    if "current_test" in st.session_state:
        st.markdown(st.session_state.current_test)
        user_answers = st.text_area("Type your answers here...")
        if st.button("Submit for Grading"):
            grade_prompt = f"Grade these answers based on this test: {st.session_state.current_test}. Answers: {user_answers}. Give a score out of 10."
            grade = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": grade_prompt}])
            st.write(grade.choices[0].message.content)

# C. Quiz Mode
elif menu == "Quiz Mode":
    st.title("📝 Instant Quiz")
    q_topic = st.text_input("Enter topic for a quick quiz:")
    if q_topic and st.button("Generate Quiz"):
        res = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": f"Create a 5-question multiple choice quiz on {q_topic} with answers at the bottom."}])
        st.markdown(res.text if hasattr(res, 'text') else res.choices[0].message.content)

# D. History
elif menu == "History":
    st.title("📜 Chat History")
    history = supabase.table("history").select("*").eq("user_id", st.session_state.user_id).order("created_at", desc=True).execute()
    for entry in history.data:
        st.text(f"[{entry['created_at'][:16]}] {entry['role'].upper()}: {entry['content'][:100]}...")
