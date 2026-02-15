import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="centered", page_icon="🎓")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini with Auto-Bug-Fixing Logic
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

@st.cache_resource
def initialize_ai():
    """Tries different model names to bypass the 404 bug"""
    possible_models = ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']
    for model_name in possible_models:
        try:
            m = genai.GenerativeModel(model_name)
            # Test call to ensure it's not a 404
            m.generate_content("test")
            return m
        except:
            continue
    return None

model = initialize_ai()

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. GOOGLE AUTH & AUTH UI ---
def login_page():
    st.title("🎓 Study Master Pro")
    st.markdown("### Elevate your learning with AI")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", placeholder="yourname@example.com")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
        
        with col2:
            # Google Sign-In Simulation (Redirects to Supabase OAuth)
            if st.button("🌐 Sign in with Google", use_container_width=True):
                try:
                    # Note: Requires Google Provider enabled in Supabase Dashboard
                    res = supabase.auth.sign_in_with_oauth({"provider": "google"})
                    st.info("Redirecting to Google...")
                except Exception as e:
                    st.error("Google Sign-in not configured in Supabase.")

    with tab2:
        new_email = st.text_input("Register Email", placeholder="yourname@example.com")
        new_pass = st.text_input("Create Password", type="password")
        if st.button("Create Account", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_pass})
                st.success("Registration successful! Please log in.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- 4. DATA LOGIC (24h Reset) ---
def get_daily_usage():
    """Fetches usage from Supabase within last 24h"""
    try:
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).gte("created_at", yesterday).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 5. MAIN APP INTERFACE ---
if st.session_state.user:
    # Sidebar Setup
    st.sidebar.title("💎 Study Master")
    
    # Redemption Zone
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM PREMIUM"):
            code = st.text_input("Enter Code", type="password")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("Premium Active (250 Chats)")

    # Navigation & Usage
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.progress(min(usage/limit, 1.0))
    st.sidebar.write(f"Usage: {usage}/{limit} (Resets in 24h)")
    
    menu = st.sidebar.radio("Features", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode", "Schedule Fixer"])
    
    if st.sidebar.button("Log Out"):
        st.session_state.user = None
        st.rerun()

    # Feature Logic
    if not model:
        st.error("🚨 AI Model could not be initialized. Please check your API Key in secrets.")
    elif usage >= limit:
        st.error(f"Daily limit reached! Use a Premium code to get 250 chats.")
    else:
        # Load the feature functions (as defined in previous steps)
        if menu == "Normal Chat":
            st.subheader("💬 AI Study Chat")
            prompt = st.chat_input("How can I help you today?")
            if prompt:
                with st.chat_message("user"): st.write(prompt)
                resp = model.generate_content(prompt)
                with st.chat_message("assistant"): st.write(resp.text)
                supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
        
        elif menu == "Quiz Zone":
            st.subheader("📝 Quick Quiz")
            topic = st.text_input("Quiz Topic")
            if topic and st.button("Generate"):
                st.write(model.generate_content(f"Generate 5 MCQs for {topic}").text)

        elif menu == "File Mode":
            st.subheader("📁 Notes from Files")
            file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            if file:
                img = PIL.Image.open(file)
                st.write(model.generate_content(["Summarize this study material", img]).text)

else:
    login_page()
