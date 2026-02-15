import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="centered", page_icon="🎓")

# --- 2. SAFE INITIALIZATION WITH ERROR HANDLING ---
@st.cache_resource
def initialize_supabase():
    """Initialize Supabase with error handling"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"🚨 Supabase initialization failed: {e}")
        return None

@st.cache_resource
def initialize_gemini():
    """Initialize Gemini AI - FIXED for stable API only"""
    try:
        # Check if API key exists
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("🚨 GOOGLE_API_KEY not found in secrets!")
            return None
        
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # Only use STABLE models that work with standard API keys
        model_names = [
            'gemini-1.5-flash',  # Most common, works for everyone
            'gemini-1.5-pro',    # Fallback
            'gemini-pro'         # Legacy fallback
        ]
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                return model
            except Exception:
                continue
        
        st.error("🚨 Could not initialize any model. Check your API key.")
        return None
        
    except Exception as e:
        st.error(f"🚨 AI initialization failed: {str(e)}")
        return None

# Initialize services
supabase = initialize_supabase()
model = initialize_gemini()

# --- 3. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 4. USAGE TRACKER (24H RESET) ---
def get_daily_usage():
    """Checks Supabase for messages in the last 24 hours"""
    if not supabase or not st.session_state.user:
        return 0
    try:
        time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq(
            "user_id", st.session_state.user.id
        ).gte("created_at", time_threshold).execute()
        return res.count if res.count else 0
    except Exception:
        return 0

# --- 5. LOGIN SCREEN ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    if not supabase:
        st.error("Cannot connect to authentication service. Check your Supabase credentials.")
        return
    
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])
    
    with tab_login:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Log In", use_container_width=True):
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password({
                            "email": email, 
                            "password": password
                        })
                        st.session_state.user = res.user
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login Failed: {str(e)}")
        
        with col2:
            if st.button("🌐 Google Sign-In", use_container_width=True):
                try:
                    supabase_url = st.secrets["supabase"]["url"]
                    redirect_url = "http://localhost:8501"  # Change for deployment
                    
                    oauth_url = f"{supabase_url}/auth/v1/authorize?provider=google&redirect_to={redirect_url}"
                    
                    st.markdown(f'[🔗 Click to sign in with Google]({oauth_url})')
                    st.info("Enable Google OAuth in Supabase Dashboard → Auth → Providers")
                except Exception as e:
                    st.error(f"Google auth error: {e}")

    with tab_signup:
        s_email = st.text_input("New Email", key="s_email")
        s_pass = st.text_input("New Password (min 6 characters)", type="password", key="s_pass")
        s_pass_confirm = st.text_input("Confirm Password", type="password", key="s_pass_confirm")
        
        if st.button("Sign Up", use_container_width=True):
            if not s_email or not s_pass:
                st.error("Please fill in all fields")
            elif len(s_pass) < 6:
                st.error("Password must be at least 6 characters")
            elif s_pass != s_pass_confirm:
                st.error("Passwords do not match")
            else:
                try:
                    res = supabase.auth.sign_up({
                        "email": s_email, 
                        "password": s_pass
                    })
                    st.success("✅ Account created! Check your email to verify, then log in.")
                except Exception as e:
                    st.error(f"Signup Failed: {str(e)}")

# --- 6. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("🚨 AI service unavailable. Please check your GOOGLE_API_KEY.")
        st.info("Get your key at: https://aistudio.google.com/app/apikey")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master")
    
    # Premium Code
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM PREMIUM CODE"):
            code = st.text_input("Enter Code", type="password", key="premium_code")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium Activated!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("✨ Premium Active (250 Chats)")

    # Usage Meter
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{usage} / {limit}")
    st.sidebar.progress(min(usage/limit, 1.0))

    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Quiz Zone", "File Mode", "Socratic Tutor"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # --- FEATURES ---
    if usage >= limit:
        st.error(f"⚠️ Daily limit reached ({usage}/{limit}). Upgrade or wait 24 hours.")
    else:
        if menu == "Normal Chat":
            st.subheader("💬 AI Study Chat")
            prompt = st.chat_input("Ask a question...")
            if prompt:
                with st.chat_message("user"): 
                    st.write(prompt)
                
                try:
                    with st.spinner("Thinking..."):
                        response = model.generate_content(prompt)
                    
                    with st.chat_message("assistant"): 
                        st.write(response.text)
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id, 
                            "question": prompt, 
                            "answer": response.text
                        }).execute()
                        
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Quiz Zone":
            st.subheader("📝 Quiz Zone")
            topic = st.text_input("Enter a topic:")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            
            if topic and st.button("Generate Quiz"):
                try:
                    with st.spinner("Creating quiz..."):
                        res = model.generate_content(
                            f"Create a 5-question multiple choice quiz about {topic} at {difficulty} difficulty. "
                            f"Format: Question, then A) B) C) D) options, then blank line before next question."
                        )
                    st.markdown(res.text)
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Quiz: {topic}",
                            "answer": res.text
                        }).execute()
                        
                except Exception as e:
                    st.error(f"Error: {e}")

        elif menu == "File Mode":
            st.subheader("📁 Study from Files")
            file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if file:
                try:
                    img = PIL.Image.open(file)
                    st.image(img, caption="Uploaded Image", use_container_width=True)
                    
                    if st.button("Analyze Image"):
                        with st.spinner("Analyzing..."):
                            res = model.generate_content([
                                "Analyze this study material. Provide: 1) Summary of key concepts "
                                "2) Important points 3) Study tips", 
                                img
                            ])
                        st.write(res.text)
                        
                        if supabase:
                            supabase.table("history").insert({
                                "user_id": st.session_state.user.id,
                                "question": "Image Analysis",
                                "answer": res.text
                            }).execute()
                            
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Socratic Tutor":
            st.subheader("🎯 Socratic Tutor")
            st.info("Learn through guided questions instead of direct answers.")
            
            problem = st.text_area("Describe your problem:")
            
            if problem and st.button("Start Session"):
                try:
                    with st.spinner("Preparing..."):
                        res = model.generate_content(
                            f"Act as a Socratic tutor for: '{problem}'. "
                            f"Ask 3-4 guiding questions to help discover the answer. "
                            f"Don't give direct answers."
                        )
                    st.write(res.text)
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Socratic: {problem}",
                            "answer": res.text
                        }).execute()
                        
                except Exception as e:
                    st.error(f"Error: {e}")

else:
    login_screen()
