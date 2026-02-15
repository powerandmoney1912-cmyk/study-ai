import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="centered", page_icon="🎓")

# Initialize Supabase
# Ensure these match your Streamlit Secrets exactly!
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- THE BUG KILLER: UNIVERSAL MODEL LOADER ---
import google.generativeai as genai

# Configure the API Key from secrets
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

@st.cache_resource
def load_universal_model():
    """Tries different paths to bypass the 404 bug"""
    # We try 'gemini-1.5-flash' first as it's the most stable current name
    for model_id in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(model_id)
            # Send a tiny test message to confirm it works
            m.generate_content("hi") 
            return m
        except Exception:
            continue
    return None

model = load_universal_model()

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. USAGE TRACKER (24H RESET) ---
def get_daily_usage():
    """Checks Supabase for messages in the last 24 hours"""
    try:
        time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).gte("created_at", time_threshold).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. PERFECT LOGIN & GOOGLE SIGN-IN ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    # Modern Tabbed Interface
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Log In", use_container_width=True):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login Failed: {e}")
        
        with col2:
            # FIXED GOOGLE SIGN-IN
            # Requires Google Provider to be enabled in Supabase Dashboard -> Auth -> Providers
            if st.button("🌐 Sign in with Google", use_container_width=True):
                try:
                    # Redirects to Google Auth via Supabase
                    supabase.auth.sign_in_with_oauth({
                        "provider": "google",
                        "options": {"redirectTo": "https://your-app-url.streamlit.app"} # Update this to your URL
                    })
                except Exception as e:
                    st.error("Google Auth not configured in Supabase.")

    with tab_signup:
        s_email = st.text_input("New Email", key="s_email")
        s_pass = st.text_input("New Password", type="password", key="s_pass")
        if st.button("Sign Up", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": s_email, "password": s_pass})
                st.success("Account created! Now switch to the Login tab.")
            except Exception as e:
                st.error(f"Signup Failed: {e}")

# --- 5. MAIN APP ---
if st.session_state.user:
    # Sidebar: Premium & Navigation
    st.sidebar.title("💎 Study Master")
    
    # Redemption Zone
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM PREMIUM CODE"):
            code = st.text_input("Enter Code", type="password")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("Premium Active (250 Chats)")

    # 24h Usage Meter
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{usage} / {limit}")
    st.sidebar.progress(min(usage/limit, 1.0))

    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Quiz Zone", "File Mode", "Socratic Tutor"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # --- FEATURE LOGIC ---
    if not model:
        st.error("🚨 AI Model Error: The system could not find a working Gemini model. Check your API key.")
    elif usage >= limit:
        st.error(f"Daily limit reached ({usage}/{limit}). Use a code or wait for the 24h reset.")
    else:
        if menu == "Normal Chat":
            st.subheader("💬 AI Study Chat")
            prompt = st.chat_input("Ask a question...")
            if prompt:
                with st.chat_message("user"): st.write(prompt)
                response = model.generate_content(prompt)
                with st.chat_message("assistant"): st.write(response.text)
                # Save to Supabase History
                supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": response.text}).execute()
        
        elif menu == "Quiz Zone":
            st.subheader("📝 Quiz Zone")
            topic = st.text_input("Enter a topic:")
            if topic and st.button("Generate Quiz"):
                res = model.generate_content(f"Create a 5-question multiple choice quiz about {topic}.")
                st.markdown(res.text)

        elif menu == "File Mode":
            st.subheader("📁 Study from Files")
            file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            if file:
                img = PIL.Image.open(file)
                res = model.generate_content(["Provide detailed notes based on this image", img])
                st.write(res.text)
else:
    login_screen()

