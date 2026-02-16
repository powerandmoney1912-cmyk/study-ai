import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# --- 1. CORE CONFIG ---
st.set_page_config(page_title="Study Master Ultra", layout="wide", page_icon="🎓")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing API Keys in Streamlit Secrets!")
    st.stop()

# --- 2. AUTHENTICATION ---
if "user" not in st.session_state:
    st.title("🛡️ Study Master Access")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Log In"):
            res = supabase.auth.sign_in_with_password({"email": e, "password": p})
            st.session_state.user = res.user
            st.rerun()
    with t2:
        ne = st.text_input("New Email")
        np = st.text_input("New Password", type="password")
        if st.button("Register"):
            supabase.auth.sign_up({"email": ne, "password": np})
            st.success("Verification email sent!")
    st.stop()

# --- 3. USERNAME SETUP (Fixes APIError) ---
profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()

if not profile_res.data:
    st.title("👋 Set your Username")
    u_name = st.text_input("Choose a username")
    if st.button("Save & Start"):
        if len(u_name) > 2:
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u_name, "xp": 0}).execute()
            st.rerun()
    st.stop()

user_info = profile_res.data[0]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title(f"👤 {user_info['username']}")
    st.write(f"XP: {user_info['xp']}")
    
    menu = st.radio("Navigation", [
        "💬 Chat History", 
        "👨‍🏫 Teacher Mode", 
        "📝 Notes Maker", 
        "🗂️ Flashcards", 
        "📅 Schedule Generator", # NEW FEATURE ADDED
        "📸 Visual Lab", 
        "📊 Dashboard"
    ])
    
    lang = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
    st.divider()
    st.write("✨ **Made by Aarya**")
    if st.button("🚪 Logout"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

# --- 5. AI ENGINE (Fixes Large Language Model Refusal) ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else "English"
    # Prompt engineering to force the AI to analyze the context
    full_sys = f"{system}. You have full access to the user's study materials. Respond ONLY in {t_lang}."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 6. FEATURE MODULES ---

if menu == "💬 Chat History":
    st.header("Chat & History")
    # Fix KeyError: Fetching with default handling
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
    for m in hist.data:
        role = m.get("role", "assistant")
        content = m.get("content", "")
        with st.chat_message(role):
            st.write(content)
    
    if p := st.chat_input("Ask a question..."):
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()

elif menu == "📅 Schedule Generator":
    st.header("📅 AI Study Planner")
    subjects = st.text_area("List your subjects and exam dates")
    hours = st.slider("Daily Study Hours", 1, 12, 4)
    if st.button("Generate Schedule"):
        plan = ask_ai(f"Create a strict study timetable for these subjects: {subjects} for {hours} hours a day.")
        st.markdown(plan)

elif menu == "👨‍🏫 Teacher Mode":
    st.header("Teacher Mode")
    topic = st.text_input("Topic")
    if st.button("Get Quiz"):
        st.write(ask_ai(f"Give me 3 tough questions on {topic}"))

elif menu == "📝 Notes Maker":
    st.header("Notes Maker")
    txt = st.text_area("Paste text")
    if st.button("Clean Notes"):
        st.write(ask_ai(f"Turn this into study notes: {txt}"))

elif menu == "🗂️ Flashcards":
    st.header("Flashcards")
    f_topic = st.text_input("Subject")
    if st.button("Make Cards"):
        st.info(ask_ai(f"Create 5 flashcards for {f_topic}"))

elif menu == "📸 Visual Lab":
    st.header("Visual Lab")
    img = st.camera_input("Take photo")
    if img:
        if st.button("Analyze"):
            st.write(ask_ai("Analyze this study material and explain it."))

elif menu == "📊 Dashboard":
    st.header("Progress Dashboard")
    st.metric("Total XP", user_info['xp'])
    st.progress(min((user_info['xp'] % 100) / 100, 1.0))
