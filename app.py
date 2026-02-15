import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image
import os

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="centered", page_icon="🎓")

# --- 2. SUPABASE INIT ---
@st.cache_resource
def initialize_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase failed: {e}")
        return None

# --- 3. BULLETPROOF GEMINI INIT - AUTO-DETECTS WORKING MODEL ---
@st.cache_resource
def initialize_gemini():
    """Most powerful auto-detection code - tries EVERYTHING"""
    try:
        # Check API key exists
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("GOOGLE_API_KEY not in secrets!")
            return None
        
        api_key = st.secrets["GOOGLE_API_KEY"].strip()
        
        if not api_key or len(api_key) < 20:
            st.error("API key too short or empty!")
            return None
        
        # Import and configure
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # STEP 1: List ALL available models from YOUR API key
        st.info("🔍 Scanning for available AI models...")
        
        try:
            all_models = genai.list_models()
            
            # Filter models that support content generation
            valid_models = [
                m for m in all_models 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            if not valid_models:
                st.error("No models support content generation with your API key!")
                st.info("Create a NEW key at: https://aistudio.google.com/app/apikey")
                return None
            
            # Show what we found
            model_names = [m.name for m in valid_models]
            st.success(f"✅ Found {len(model_names)} compatible models")
            
            # STEP 2: Try each model until one works
            for model_info in valid_models:
                model_name = model_info.name
                
                # Try with full name (e.g., "models/gemini-pro")
                try:
                    st.info(f"Testing: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    
                    # Quick test
                    response = model.generate_content("Say 'ready'")
                    if response.text:
                        st.success(f"🎉 CONNECTED TO: {model_name}")
                        return model
                except Exception as e:
                    st.warning(f"❌ {model_name} failed: {str(e)[:50]}")
                
                # Try without "models/" prefix
                try:
                    short_name = model_name.replace("models/", "")
                    st.info(f"Testing: {short_name}")
                    model = genai.GenerativeModel(short_name)
                    
                    response = model.generate_content("Say 'ready'")
                    if response.text:
                        st.success(f"🎉 CONNECTED TO: {short_name}")
                        return model
                except Exception as e:
                    st.warning(f"❌ {short_name} failed: {str(e)[:50]}")
            
            # If we get here, nothing worked
            st.error("All models failed to initialize!")
            st.error("Your API key may be:")
            st.error("1. Expired")
            st.error("2. From wrong service (Vertex AI vs AI Studio)")
            st.error("3. Invalid or restricted")
            st.info("Solution: Generate NEW key at https://aistudio.google.com/app/apikey")
            return None
            
        except Exception as e:
            st.error(f"Failed to list models: {str(e)}")
            st.error("This usually means:")
            st.error("1. Invalid API key format")
            st.error("2. Network/permission issue")
            st.error("3. Using wrong Google service")
            st.info("Get new key: https://aistudio.google.com/app/apikey")
            return None
            
    except Exception as e:
        st.error(f"Fatal error: {str(e)}")
        return None

# Initialize
supabase = initialize_supabase()
model = initialize_gemini()

# --- 4. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 5. USAGE TRACKER ---
def get_daily_usage():
    if not supabase or not st.session_state.user:
        return 0
    try:
        time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq(
            "user_id", st.session_state.user.id
        ).gte("created_at", time_threshold).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 6. LOGIN SCREEN ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    if not supabase:
        st.error("Supabase connection failed.")
        return
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("Log In", use_container_width=True):
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
            else:
                st.error("Enter email and password")
    
    with tab2:
        new_email = st.text_input("Email", key="s_email")
        new_pass = st.text_input("Password (6+ chars)", type="password", key="s_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="s_confirm")
        
        if st.button("Create Account", use_container_width=True):
            if not new_email or not new_pass:
                st.error("Fill all fields")
            elif len(new_pass) < 6:
                st.error("Password too short")
            elif new_pass != confirm_pass:
                st.error("Passwords don't match")
            else:
                try:
                    supabase.auth.sign_up({"email": new_email, "password": new_pass})
                    st.success("Account created! Check email to verify.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

# --- 7. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("⚠️ AI unavailable. Check errors above.")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master")
    
    # Premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 Premium Code"):
            code = st.text_input("Code", type="password", key="prem")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
                else:
                    st.error("Invalid")
    else:
        st.sidebar.success("✨ Premium Active")
    
    # Usage
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{usage}/{limit}")
    st.sidebar.progress(min(usage/limit, 1.0))
    
    menu = st.sidebar.radio("Menu", ["Chat", "Quiz", "Image", "Tutor"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    # Features
    if usage >= limit:
        st.error(f"Limit reached ({usage}/{limit})")
    else:
        if menu == "Chat":
            st.subheader("💬 Chat")
            q = st.chat_input("Ask...")
            if q:
                with st.chat_message("user"):
                    st.write(q)
                try:
                    resp = model.generate_content(q)
                    with st.chat_message("assistant"):
                        st.write(resp.text)
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": q,
                            "answer": resp.text
                        }).execute()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Quiz":
            st.subheader("📝 Quiz")
            topic = st.text_input("Topic:")
            diff = st.selectbox("Level", ["Easy", "Medium", "Hard"])
            if topic and st.button("Generate"):
                try:
                    resp = model.generate_content(f"5 multiple choice questions about {topic} ({diff} level)")
                    st.markdown(resp.text)
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Quiz: {topic}",
                            "answer": resp.text
                        }).execute()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Image":
            st.subheader("📁 Image Analysis")
            file = st.file_uploader("Upload", type=['jpg', 'png', 'jpeg'])
            if file:
                try:
                    img = PIL.Image.open(file)
                    st.image(img, use_container_width=True)
                    if st.button("Analyze"):
                        resp = model.generate_content(["Explain this study material in detail", img])
                        st.write(resp.text)
                        if supabase:
                            supabase.table("history").insert({
                                "user_id": st.session_state.user.id,
                                "question": "Image",
                                "answer": resp.text
                            }).execute()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Tutor":
            st.subheader("🎯 Socratic Tutor")
            prob = st.text_area("Your problem:")
            if prob and st.button("Start"):
                try:
                    resp = model.generate_content(f"Socratic tutor for: {prob}. Ask guiding questions only.")
                    st.write(resp.text)
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Tutor: {prob}",
                            "answer": resp.text
                        }).execute()
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    login_screen()
