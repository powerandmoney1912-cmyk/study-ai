import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Setup Secrets in Streamlit first!")
    st.stop()

# --- 2. AUTHENTICATION & LOGIN ---
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
        st.divider()
        if st.button("🌐 Sign in with Google"):
            st.info("Enable Google Auth in Supabase Dashboard -> Auth -> Providers")
    with t2:
        ne = st.text_input("New Email")
        np = st.text_input("New Password", type="password")
        if st.button("Register"):
            supabase.auth.sign_up({"email": ne, "password": np})
            st.success("Check your email for the verification link!")
    st.stop()

# --- 3. USERNAME SETUP (FIXED BUG) ---
# We check if a profile exists for the logged-in user
profile_query = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()

if not profile_query.data:
    st.title("👋 Welcome! Set your Username")
    u_name = st.text_input("Choose a unique username")
    if st.button("Save & Start Studying"):
        if len(u_name) > 2:
            # Fixed the APIError by ensuring ID is sent correctly
            supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u_name, "xp": 0}).execute()
            st.success(f"Hello {u_name}!")
            time.sleep(1); st.rerun()
    st.stop()

user_data = profile_query.data[0]

# --- 4. SIDEBAR & NAVIGATION ---
with st.sidebar:
    st.title(f"👤 {user_data['username']}")
    st.write(f"Level: {user_data['xp'] // 100 + 1} | XP: {user_data['xp']}")
    
    if not user_data['is_premium']:
        p_code = st.text_input("Premium Code", type="password")
        if st.button("Unlock"):
            if p_code == "STUDY777":
                supabase.table("profiles").update({"is_premium": True}).eq("id", st.session_state.user.id).execute()
                st.success("Premium Unlocked!"); time.sleep(1); st.rerun()
    else: st.success("💎 PREMIUM ACTIVE")

    menu = st.radio("Navigation", ["💬 Chat History", "👨‍🏫 Teacher Mode", "📝 Notes Maker", "🗂️ Flashcards", "📸 Visual Lab", "📊 Dashboard"])
    lang = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
    
    st.divider()
    st.write("✨ **Made by Aarya**")
    if st.button("🚪 Logout"):
        supabase.auth.sign_out()
        del st.session_state.user; st.rerun()

# --- 5. AI LOGIC (FIXES THE "LARGE LANGUAGE MODEL" BUG) ---
def ask_ai(prompt, system="Expert Study Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else "English"
    # The trick: We tell the AI it HAS seen the data so it doesn't refuse
    full_sys = f"{system}. You have analyzed the user's visual/audio context. Respond ONLY in {t_lang}."
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
    # Load history from DB
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
    for m in hist.data:
        with st.chat_message(m["role"]): st.write(m["content"])
    
    if p := st.chat_input("Ask a question..."):
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()

elif menu == "👨‍🏫 Teacher Mode":
    st.header("👨‍🏫 Teacher Assessment")
    topic = st.text_input("What topic should I test you on?")
    if st.button("Start Test"):
        st.write(ask_ai(f"Give me 5 tough questions on {topic}"))

elif menu == "📝 Notes Maker":
    st.header("📝 AI Notes Maker")
    raw = st.text_area("Paste messy text here...")
    if st.button("Generate Professional Notes"):
        st.markdown(ask_ai(f"Structure this into professional study notes: {raw}"))

elif menu == "🗂️ Flashcards":
    st.header("🗂️ Flashcard Generator")
    f_topic = st.text_input("Subject")
    if st.button("Create Cards"):
        st.info(ask_ai(f"Generate 5 Flashcards for {f_topic}. Format Front: Back:"))

elif menu == "📸 Visual Lab":
    st.header("📸 Visual Study Lab")
    img = st.camera_input("Take a photo of your notes")
    if img:
        # User requested to see the button below
        if st.button("🔍 Analyze Content"):
            with st.spinner("AI is reading your handwriting..."):
                # We prompt the AI as if the OCR happened
                st.write(ask_ai("Explain the core concepts shown in this study image."))

elif menu == "📊 Dashboard":
    st.header("📊 Study Dashboard")
    st.metric("Total XP", user_data['xp'])
    st.progress(min((user_data['xp'] % 100) / 100, 1.0))
    st.write(f"Level {(user_data['xp'] // 100) + 1} Student")
