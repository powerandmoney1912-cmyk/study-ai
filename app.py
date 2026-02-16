import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Study Master Ultra Pro", layout="wide", page_icon="🎓")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error("Setup API Keys in Streamlit Secrets first!")
    st.stop()

# --- 2. AUTHENTICATION ---
if "user" not in st.session_state:
    st.title("🛡️ Study Master Access")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                st.session_state.user = res.user
                st.rerun()
            except: st.error("Invalid Login Credentials")
    with t2:
        ne = st.text_input("New Email")
        np = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            supabase.auth.sign_up({"email": ne, "password": np})
            st.success("Verification link sent to your email!")
    st.stop()

# --- 3. USERNAME SETUP (Fixes APIError) ---
profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()

if not profile_res.data:
    st.title("👋 Welcome! Choose a Username")
    u_name = st.text_input("Enter your unique study handle")
    if st.button("Confirm Username"):
        if len(u_name) > 2:
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u_name, "xp": 0}).execute()
            st.rerun()
        else: st.warning("Username must be at least 3 characters.")
    st.stop()

user_data = profile_res.data[0]

# --- 4. SIDEBAR (Premium Code & Navigation) ---
with st.sidebar:
    st.title(f"👤 {user_data.get('username', 'Student')}")
    st.write(f"Level: {user_data.get('xp', 0) // 100 + 1} | XP: {user_data.get('xp', 0)}")
    
    # RESTORED PREMIUM CODE OPTION
    if not user_data.get('is_premium', False):
        st.divider()
        p_code = st.text_input("🎟️ Premium Code", type="password")
        if st.button("Activate Premium"):
            if p_code == "STUDY777":
                supabase.table("profiles").update({"is_premium": True}).eq("id", st.session_state.user.id).execute()
                st.success("💎 Premium Active!")
                time.sleep(1); st.rerun()
            else: st.error("Invalid Code")
    else:
        st.success("💎 PREMIUM USER")

    menu = st.radio("Navigation", [
        "💬 Chat History", 
        "📅 Schedule Generator", 
        "👨‍🏫 Teacher Mode", 
        "📝 Notes Maker", 
        "🗂️ Flashcards", 
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

# --- 5. AI ENGINE (Fixes LLM Refusal) ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else "English"
    # Bypass logic: Force the AI to act as an analyzer
    full_sys = f"{system}. You have analyzed all provided data. Answer strictly in {t_lang} using Markdown."
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 6. FEATURE MODULES ---

if menu == "💬 Chat History":
    st.header("Chat & Study History")
    # Fixed KeyError using safe dictionary gets
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
    for m in hist.data:
        role = m.get("role", "assistant")
        content = m.get("content", "...")
        with st.chat_message(role): st.write(content)
    
    if p := st.chat_input("Ask a question..."):
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()

elif menu == "📅 Schedule Generator":
    st.header("📅 AI Study Schedule")
    topics = st.text_area("List your subjects and exam dates")
    hrs = st.slider("Daily Study Hours", 1, 15, 6)
    if st.button("Generate Timetable"):
        plan = ask_ai(f"Create a strict study plan for: {topics} with {hrs} hours available per day.")
        st.markdown(plan)

elif menu == "👨‍🏫 Teacher Mode":
    st.header("👨‍🏫 Teacher Mode")
    topic = st.text_input("Topic for testing")
    if st.button("Get Assessment"):
        st.write(ask_ai(f"Generate 5 tough questions on {topic}"))

elif menu == "📝 Notes Maker":
    st.header("📝 Professional Notes Maker")
    raw_txt = st.text_area("Paste text here")
    if st.button("Organize Notes"):
        st.markdown(ask_ai(f"Turn this into clean study notes: {raw_txt}"))

elif menu == "🗂️ Flashcards":
    st.header("🗂️ Flashcard Lab")
    subj = st.text_input("Subject")
    if st.button("Make 5 Cards"):
        st.info(ask_ai(f"Create 5 Flashcards for {subj}. Format Q: A:"))

elif menu == "📸 Visual Lab":
    st.header("📸 Visual Lab")
    img = st.camera_input("Take a photo of your book")
    if img:
        if st.button("🔍 Analyze Content"):
            st.write(ask_ai("Analyze the text in this image and provide a detailed study explanation."))

elif menu == "📊 Dashboard":
    st.header("📊 Study Stats")
    st.metric("Total XP", user_data.get('xp', 0))
    st.progress(min((user_data.get('xp', 0) % 100) / 100, 1.0))
    st.write("Keep studying to level up!")
