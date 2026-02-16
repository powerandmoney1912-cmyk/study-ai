import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time
import uuid

# --- 1. CORE CONFIGURATION ---
st.set_page_config(page_title="Study Master Ultra Pro", layout="wide", page_icon="🎓")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing in Secrets!")
    st.stop()

# --- 2. AUTHENTICATION & PROFILE LOGIC ---
if "user" not in st.session_state:
    st.title("🛡️ Study Master Gateway")
    auth_tab1, auth_tab2 = st.tabs(["Login", "Create Account"])
    
    with auth_tab1:
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        if st.button("Sign In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": pwd})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Invalid credentials.")
            
    with auth_tab2:
        new_email = st.text_input("New Email")
        new_pwd = st.text_input("New Password", type="password")
        if st.button("Register"):
            supabase.auth.sign_up({"email": new_email, "password": new_pwd})
            st.success("Verification email sent! Check your inbox.")
    st.stop()

# --- 3. USERNAME SETUP CHECK ---
# Check if user has a profile/username in DB
profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()

if not profile_res.data or not profile_res.data[0].get("username"):
    st.title("👋 Welcome! Let's set up your profile.")
    u_name = st.text_input("Choose a unique username")
    if st.button("Save Username"):
        if len(u_name) > 2:
            supabase.table("profiles").upsert({"id": st.session_state.user.id, "username": u_name, "xp": 0}).execute()
            st.success(f"Welcome, {u_name}!")
            time.sleep(1)
            st.rerun()
        else: st.warning("Username too short!")
    st.stop()

# Load profile data to state
u_profile = profile_res.data[0]
st.session_state.username = u_profile["username"]
st.session_state.xp = u_profile["xp"]
st.session_state.is_premium = u_profile["is_premium"]

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🛡️ Study Master Pro")
    st.subheader(f"👤 {st.session_state.username}")
    
    # Premium Key Fix
    if not st.session_state.is_premium:
        p_code = st.text_input("Premium Code", type="password")
        if st.button("Unlock Premium"):
            if p_code == "STUDY777":
                supabase.table("profiles").update({"is_premium": True}).eq("id", st.session_state.user.id).execute()
                st.session_state.is_premium = True
                st.rerun()
    else: st.success("💎 PREMIUM ACTIVE")

    menu = st.radio("Navigation", [
        "💬 Chat & History", 
        "👨‍🏫 Teacher Mode", 
        "📝 Notes Maker", 
        "🗂️ Flashcard Lab", 
        "📷 Visual Lab",
        "📅 AI Scheduler",
        "📊 Dashboard"
    ])
    
    lang = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
    
    # Timer
    if "timer_active" not in st.session_state: st.session_state.timer_active = False
    if st.session_state.timer_active:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}")
            time.sleep(1); st.rerun()
        else:
            st.balloons(); st.session_state.timer_active = False
    else:
        mins = st.number_input("Focus Minutes", 1, 180, 25)
        if st.button("🚀 Start"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

    st.divider()
    st.write("✨ **Made by Aarya**")
    st.write("❤️ *Always here to help you study!*")
    if st.button("🚪 Logout"):
        supabase.auth.sign_out()
        del st.session_state.user
        st.rerun()

# --- 5. AI ENGINE ---
def ask_ai(prompt, system="Expert Study Assistant"):
    t_lang = "Tamil" if "Tamil" in lang else "English"
    full_sys = f"{system}. Respond in {t_lang}. Use markdown for professional formatting."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"AI Error: {e}"

# --- 6. FEATURE MODULES ---

if menu == "💬 Chat & History":
    st.header("Chat History & Assistant")
    # Load history from DB
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
    for m in hist.data:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Ask a question..."):
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        # Save to DB
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()

elif menu == "👨‍🏫 Teacher Mode":
    st.header("Teacher Assessment")
    topic = st.text_input("Enter Topic for Test")
    if st.button("Generate 5 Questions"):
        st.session_state.current_test = ask_ai(f"Give 5 quiz questions for: {topic}")
    
    if "current_test" in st.session_state:
        st.info(st.session_state.current_test)
        ans = st.text_area("Your Answers:")
        if st.button("Submit & Grade"):
            res = ask_ai(f"Grade these answers: {ans} based on questions: {st.session_state.current_test}")
            st.success(res)
            supabase.table("profiles").update({"xp": st.session_state.xp + 50}).eq("id", st.session_state.user.id).execute()

elif menu == "📝 Notes Maker":
    st.header("Professional Notes Maker")
    raw = st.text_area("Paste text or lecture points here...")
    if st.button("✨ Create Structured Notes"):
        notes = ask_ai(f"Turn this into organized study notes with headings: {raw}")
        st.markdown(notes)
        if st.button("💾 Save to My Library"):
            supabase.table("study_notes").insert({"user_id": st.session_state.user.id, "title": "New Note", "content": notes}).execute()
            st.toast("Saved!")

elif menu == "🗂️ Flashcard Lab":
    st.header("Flashcard Lab")
    f_topic = st.text_input("Flashcard Subject")
    if st.button("Generate"):
        cards = ask_ai(f"Generate 5 Flashcards for {f_topic}. Format: Q: | A:")
        st.markdown(cards)

elif menu == "📷 Visual Lab":
    st.header("Visual Lab")
    img = st.camera_input("Snapshot")
    if img:
        if st.button("🔍 Explain Image Content"):
            st.write(ask_ai("Analyze this visual study content and explain it clearly."))

elif menu == "📊 Dashboard":
    st.header("Your Progress")
    col1, col2 = st.columns(2)
    col1.metric("Current XP", st.session_state.xp)
    col2.metric("Level", (st.session_state.xp // 100) + 1)
    st.progress(min((st.session_state.xp % 100) / 100, 1.0))
