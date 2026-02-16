import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Check Secrets!")
    st.stop()

# --- 2. PERSISTENCE LAYER ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "current_test_questions" not in st.session_state:
    st.session_state.current_test_questions = None

# --- 3. DATABASE LOGIC ---
def get_usage():
    try:
        limit_time = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user_uuid).gte("created_at", limit_time).execute()
        return res.count if res.count else 0
    except: return 0

def save_to_db(role, content, type="text"):
    try:
        supabase.table("history").insert({"user_id": st.session_state.user_uuid, "role": role, "content": content, "interaction_type": type}).execute()
    except: pass

# --- 4. SIDEBAR ---
st.sidebar.title("🎓 Study Master Pro")
if not st.session_state.is_premium:
    code = st.sidebar.text_input("Premium Code", type="password")
    if st.sidebar.button("Redeem") and code == "STUDY777":
        st.session_state.is_premium = True
        st.rerun()

usage = get_usage()
limit = 250 if st.session_state.is_premium else 50
st.sidebar.metric("24h Usage", f"{usage}/{limit}")

menu = st.sidebar.selectbox("Features", ["Chat Assistant", "Teacher Mode (Test)", "File Lab", "AI Scheduler"])

# --- SIGNATURE ---
st.sidebar.markdown("---")
st.sidebar.write("✨ **Made by Aarya**")
st.sidebar.write("❤️ *Made with love*")

# --- 5. AI ENGINE ---
def ask_ai(prompt, system="You are a helpful study tutor."):
    if usage >= limit: return "LIMIT_REACHED"
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 6. MODULES ---

# A. CHAT ASSISTANT
if menu == "Chat Assistant":
    st.header("💬 Study Chat")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        ans = ask_ai(prompt)
        if ans == "LIMIT_REACHED": st.error("Limit reached!")
        else:
            with st.chat_message("assistant"): st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            save_to_db("user", prompt); save_to_db("assistant", ans)

# B. TEACHER MODE (WITH ANSWERING PART)
elif menu == "Teacher Mode (Test)":
    st.header("👨‍🏫 Teacher Mode: Assessment")
    
    # Step 1: Generate Questions
    topic = st.text_input("What subject or topic should I test you on?")
    if st.button("Generate Questions"):
        with st.spinner("Preparing test..."):
            questions = ask_ai(f"Give me 5 challenging questions about {topic}. Do not provide answers.")
            st.session_state.current_test_questions = questions
            st.session_state.current_topic = topic

    # Step 2: Answering Part
    if st.session_state.current_test_questions:
        st.divider()
        st.subheader("Questions:")
        st.info(st.session_state.current_test_questions)
        
        st.subheader("Your Answers:")
        user_answers = st.text_area("Type your answers here (label them 1 to 5):", height=200)
        
        if st.button("Submit & Get Results"):
            with st.spinner("Grading..."):
                grading_prompt = f"""
                Topic: {st.session_state.current_topic}
                Questions: {st.session_state.current_test_questions}
                User's Answers: {user_answers}
                
                Please grade these answers strictly. Provide a total score out of 10 and 
                explain which ones were correct and what needs improvement.
                """
                results = ask_ai(grading_prompt)
                st.success("### Results & Feedback")
                st.markdown(results)
                save_to_db("teacher", results, "test_result")

# C. FILE LAB
elif menu == "File Lab":
    st.header("📁 File to Notes")
    uploaded_file = st.file_uploader("Upload PDF or Image", type=['png', 'jpg', 'pdf'])
    if uploaded_file and st.button("Generate Summary"):
        notes = ask_ai(f"I've uploaded {uploaded_file.name}. Summarize the core concepts of this topic for me.")
        st.write(notes)
        save_to_db("user", f"File: {uploaded_file.name}", "file_upload")

# D. AI SCHEDULER
elif menu == "AI Scheduler":
    st.header("📅 Timetable Generator")
    s = st.text_input("List subjects")
    h = st.slider("Hours available", 1, 12, 4)
    if st.button("Get Schedule"):
        plan = ask_ai(f"Create a table for a {h}-hour study session for: {s}.")
        st.markdown(plan)
