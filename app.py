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

# BUG FIX: Using the full model path prevents the 404 'not found' error
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
# Ensures everyone starts as FREE until they enter the code
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE HELPER ---
def get_chat_count():
    """Counts total messages for the user in Supabase history"""
    try:
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. AUTHENTICATION UI ---
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
    # --- REDEMPTION ZONE ---
    st.sidebar.title("💎 Redemption Zone")
    
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 ENTER SPECIAL CODE"):
            code = st.text_input("Special Code", type="password")
            if st.button("Unlock Premium (250 Chats)"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium Activated!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("✅ PREMIUM STATUS ACTIVE")

    # Chat Limit Display
    chats_used = get_chat_count()
    max_chats = 250 if st.session_state.is_premium else 10
    st.sidebar.metric("Usage Tracker", f"{chats_used} / {max_chats} Chats")
    
    st.sidebar.divider()
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Schedule Fixer"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

    # --- FEATURE LOGIC ---
    if chats_used >= max_chats:
        st.error(f"Limit reached ({chats_used}/{max_chats}). Enter a code in the Redemption Zone to get 250 chats!")
    else:
        if menu == "Normal Chat":
            st.subheader("💬 Normal Chat")
            prompt = st.chat_input("Ask a question...")
            if prompt:
                with st.chat_message("user"): st.write(prompt)
                try:
                    resp = model.generate_content(prompt)
                    with st.chat_message("assistant"): st.write(resp.text)
                    # Track limit in Supabase
                    supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
                except Exception as e:
                    st.error(f"AI Connection Error: {e}")

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
            book = st.text_input("What topic or book?")
            days = st.number_input("Days", min_value=1)
            if st.button("Generate Plan"):
                resp = model.generate_content(f"Create a {days} day study plan for {book}")
                st.write(resp.text)
else:
    login_ui()
