import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 404 BUG FIX: Using the absolute model path prevents the 'not found' error
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
# This ensures every new session starts as FREE
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE HELPER ---
def get_chat_count():
    """Counts messages in your Supabase 'history' table"""
    try:
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. AUTHENTICATION ---
def login_ui():
    st.title("🎓 Study Master Pro")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Error: {e}")
    with tab2:
        st.info("Already have an account? Use the Login tab.")
        email_reg = st.text_input("New Email")
        pass_reg = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": email_reg, "password": pass_reg})
                st.success("Account created! Now go to the Login tab.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- 5. MAIN APP INTERFACE ---
if st.session_state.user:
    # --- SIDEBAR REDEMPTION & STATS ---
    st.sidebar.title("💎 Account Status")
    
    # Redemption Box: Only shows if NOT premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM PREMIUM CODE"):
            redeem_code = st.text_input("Enter Code", type="password")
            if st.button("Activate 250 Chats"):
                if redeem_code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium Unlocked!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("✅ PREMIUM ACTIVE")

    # Chat Limit Display
    chats_used = get_chat_count()
    max_chats = 250 if st.session_state.is_premium else 10
    st.sidebar.metric("Chats Used", f"{chats_used} / {max_chats}")
    
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Schedule Fixer"])
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

    # --- CHAT & FEATURE LOGIC ---
    if chats_used >= max_chats:
        st.error(f"Limit reached ({chats_used}/{max_chats}). Use a Premium code to get 250 chats!")
    else:
        if menu == "Normal Chat":
            st.subheader("💬 Normal Chat")
            prompt = st.chat_input("Ask me anything...")
            if prompt:
                with st.chat_message("user"): st.write(prompt)
                try:
                    resp = model.generate_content(prompt)
                    with st.chat_message("assistant"): st.write(resp.text)
                    # Save to Supabase to track limit
                    supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
                except Exception as e:
                    st.error(f"404 Bug Fix Triggered: {e}")

        elif menu == "Socratic Tutor":
            st.subheader("🧘 Socratic Tutor")
            prompt = st.chat_input("What are you studying?")
            if prompt:
                try:
                    resp = model.generate_content(f"You are a Socratic Tutor. Ask questions only: {prompt}")
                    st.write(resp.text)
                    supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
                except Exception as e:
                    st.error(f"AI Error: {e}")

        elif menu == "Schedule Fixer":
            st.subheader("📅 Schedule Fixer")
            book = st.text_input("What are you reading?")
            days = st.number_input("Days", min_value=1)
            if st.button("Generate Plan"):
                resp = model.generate_content(f"Create a {days} day study plan for {book}")
                st.write(resp.text)
else:
    login_ui()
