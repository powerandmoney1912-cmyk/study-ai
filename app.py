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

# --- 2. BUG KILLER: PERSISTENT CHAT HISTORY ---
# This block prevents messages from disappearing
if "messages" not in st.session_state:
    st.session_state.messages = []  # List to hold the current conversation
if "user_uuid" not in st.session_state:
    st.session_state.user_uuid = str(uuid.uuid4())
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE LOGIC ---
def get_usage():
    try:
        limit_time = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user_uuid).gte("created_at", limit_time).execute()
        return res.count if res.count else 0
    except: return 0

def save_to_db(role, content, type="text"):
    try:
        supabase.table("history").insert({
            "user_id": st.session_state.user_uuid, 
            "role": role, 
            "content": content,
            "interaction_type": type
        }).execute()
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

menu = st.sidebar.selectbox("Features", ["Chat Assistant", "File & Voice Lab", "Teacher Mode", "AI Scheduler"])

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

# A. CHAT ASSISTANT (FIXED: NO DISAPPEARING MESSAGES)
if menu == "Chat Assistant":
    st.header("💬 Persistent Study Chat")
    
    # Display old messages from this session
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask a question..."):
        # Add user message to state and DB
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        ans = ask_ai(prompt)
        
        if ans == "LIMIT_REACHED":
            st.error("Limit reached! Use code STUDY777")
        else:
            with st.chat_message("assistant"):
                st.markdown(ans)
            st.session_state.messages.append({"role": "assistant", "content": ans})
            save_to_db("user", prompt)
            save_to_db("assistant", ans)

# B. FILE & VOICE LAB
elif menu == "File & Voice Lab":
    st.header("📁 Multimedia Notes")
    st.info("Upload a file or record audio to get AI summaries.")
    
    file_type = st.radio("Select Type", ["Image/PDF", "Voice Message"])
    
    if file_type == "Image/PDF":
        uploaded_file = st.file_uploader("Upload Study Material", type=['png', 'jpg', 'pdf'])
        if uploaded_file and st.button("Generate Notes"):
            # Logic: In a real app, you'd extract text here. For now, we simulate OCR:
            with st.spinner("Analyzing document..."):
                simulated_notes = ask_ai(f"I have a document titled {uploaded_file.name}. Provide a detailed study summary of what this document likely contains based on the subject.")
                st.subheader("📝 Generated Notes")
                st.write(simulated_notes)
                save_to_db("user", f"Uploaded {uploaded_file.name}", "file")
    
    else:
        audio_file = st.audio_input("Record your question")
        if audio_file and st.button("Transcribe & Answer"):
            st.warning("Note: Voice processing requires Groq Whisper API. Simulating response...")
            voice_ans = ask_ai("The user sent a voice message asking for study help. Give general encouragement and a sample study tip.")
            st.write(voice_ans)

# C. AI SCHEDULER
elif menu == "AI Scheduler":
    st.header("📅 Study Timetable Generator")
    subs = st.text_input("Subjects (e.g. Math, Physics, History)")
    hrs = st.slider("Hours per day", 1, 12, 5)
    if st.button("Create Plan"):
        plan = ask_ai(f"Create a strict {hrs}-hour study schedule for: {subs}. Format as a table.")
        st.markdown(plan)

# D. TEACHER MODE
elif menu == "Teacher Mode":
    st.header("👨‍🏫 AI Teacher")
    topic = st.text_input("Enter topic for test")
    if topic and st.button("Get Test"):
        test = ask_ai(f"Give 5 questions about {topic}. No answers.")
        st.write(test)
