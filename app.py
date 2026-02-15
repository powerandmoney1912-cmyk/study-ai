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

# Initialize Gemini 
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- THE ULTIMATE BUG FIX ---
# This loop tries every possible naming convention to bypass the 404 error
@st.cache_resource
def load_ai_model():
    # We try the most common names used by different library versions
    for model_id in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(model_id)
            # We force a tiny test call. If this fails, it jumps to 'except'
            m.generate_content("ok") 
            return m
        except:
            continue
    return None

model = load_ai_model()

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. DATABASE LOGIC ---
def get_usage():
    try:
        # 24-hour reset logic
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).gte("created_at", yesterday).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. PERFECT LOGIN PAGE ---
def show_login():
    st.title("🎓 Study Master Pro")
    st.write("Log in to access your Socratic Tutor, Quizzes, and File Analysis.")
    
    choice = st.radio("Choose Action", ["Login", "Sign Up"], horizontal=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if choice == "Login":
        if st.button("Log In", use_container_width=True):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login error: {e}")
                
        st.divider()
        if st.button("🌐 Continue with Google", use_container_width=True):
            st.info("Ensure Google Provider is enabled in Supabase Dashboard.")
            supabase.auth.sign_in_with_oauth({"provider": "google"})
            
    else:
        if st.button("Create Account", use_container_width=True):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Success! You can now switch to the Login tab.")
            except Exception as e:
                st.error(f"Sign up error: {e}")

# --- 5. MAIN INTERFACE ---
if st.session_state.user:
    # Sidebar: Redemption Zone
    st.sidebar.title("💎 Account Status")
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM CODE"):
            code = st.text_input("Premium Code", type="password")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("Premium Active: 250 Chats")

    # Usage Meter
    usage = get_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.write(f"**Usage:** {usage} / {limit}")
    st.sidebar.progress(min(usage/limit, 1.0))

    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Feature Logic
    if not model:
        st.error("🚨 AI initialization failed. Please check your GOOGLE_API_KEY in Secrets.")
    elif usage >= limit:
        st.error("24h Limit reached! Upgrade to Premium or wait for the reset.")
    else:
        if menu == "Normal Chat":
            st.subheader("💬 AI Study Chat")
            p = st.chat_input("Ask a study question...")
            if p:
                with st.chat_message("user"): st.write(p)
                r = model.generate_content(p)
                with st.chat_message("assistant"): st.write(r.text)
                supabase.table("history").insert({"user_id": st.session_state.user.id, "question": p, "answer": r.text}).execute()
        
        elif menu == "Quiz Zone":
            st.subheader("📝 Quiz Zone")
            topic = st.text_input("Enter a topic for a 5-question quiz")
            if topic and st.button("Generate Quiz"):
                st.write(model.generate_content(f"Create a quiz for {topic}").text)

        elif menu == "File Mode":
            st.subheader("📁 File Mode")
            f = st.file_uploader("Upload Image", type=['jpg', 'jpeg', 'png'])
            if f and st.button("Generate Notes"):
                img = PIL.Image.open(f)
                st.write(model.generate_content(["Summarize these study notes", img]).text)
else:
    show_login()
