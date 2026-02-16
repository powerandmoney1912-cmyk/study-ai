import streamlit as st
from datetime import datetime, timedelta, time
import json
import time as time_module

# --- SECRETS DEBUG MODE ---
# Set this to True to debug secrets, False to run normal app
DEBUG_MODE = True  # ← Change to False after fixing secrets

if DEBUG_MODE:
    st.title("🔍 Secrets Debug Tool")
    st.write("## Testing Your Secrets Configuration")
    st.warning("⚠️ DEBUG_MODE is ON. Change to False in code after fixing secrets!")
    
    # Test 1: Check if secrets exist
    st.write("### Test 1: Do secrets exist?")
    try:
        all_secrets = st.secrets
        st.success(f"✅ Secrets found! Keys: {list(all_secrets.keys())}")
    except Exception as e:
        st.error(f"❌ No secrets found: {e}")
        st.stop()
    
    # Test 2: Check Supabase section
    st.write("### Test 2: Supabase Section")
    try:
        if "supabase" in st.secrets:
            st.success("✅ 'supabase' section exists")
            st.write(f"Keys in supabase section: {list(st.secrets['supabase'].keys())}")
            
            # Check URL
            if "url" in st.secrets["supabase"]:
                url = st.secrets["supabase"]["url"]
                st.success(f"✅ URL found: {url[:30]}...")
                
                # Validate URL format
                if url.startswith("https://") and "supabase.co" in url:
                    st.success("✅ URL format looks correct!")
                else:
                    st.error(f"❌ URL format wrong. Should be: https://xxxxx.supabase.co")
                    st.error(f"Your URL: {url}")
            else:
                st.error("❌ 'url' not found in supabase section")
            
            # Check key
            if "key" in st.secrets["supabase"]:
                key = st.secrets["supabase"]["key"]
                st.success(f"✅ Key found: {key[:30]}...")
                
                # Validate key format
                if len(key) > 100:
                    st.success(f"✅ Key length looks correct! ({len(key)} characters)")
                else:
                    st.error(f"❌ Key too short: {len(key)} characters (should be 150+)")
            else:
                st.error("❌ 'key' not found in supabase section")
        else:
            st.error("❌ 'supabase' section not found")
            st.info("Available sections: " + str(list(st.secrets.keys())))
    except Exception as e:
        st.error(f"❌ Error reading supabase: {e}")
    
    # Test 3: Check Google API Key
    st.write("### Test 3: Google API Key")
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success(f"✅ GOOGLE_API_KEY found: {api_key[:15]}...")
            
            # Validate format
            if api_key.startswith("AIza"):
                st.success("✅ Key format looks correct!")
            else:
                st.error("❌ Key should start with 'AIza'")
                st.error(f"Your key starts with: {api_key[:10]}")
        else:
            st.error("❌ 'GOOGLE_API_KEY' not found")
            st.info("Available top-level keys: " + str(list(st.secrets.keys())))
    except Exception as e:
        st.error(f"❌ Error reading GOOGLE_API_KEY: {e}")
    
    st.write("---")
    st.write("## 📋 What Your Secrets Should Look Like")
    st.code("""[supabase]
url = "https://xxxxx.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

GOOGLE_API_KEY = "AIzaSyAaBbCcDdEeFfGgHhIiJjKk..."
""", language="toml")
    
    st.write("## 🔧 Next Steps")
    st.info("""
1. ✅ Check all tests above are green
2. 📝 Fix any ❌ errors in your Streamlit Cloud Secrets
3. 🔄 Click 'Reboot app' 
4. 🔁 Refresh this page
5. ✏️ Once all green, change DEBUG_MODE = False in the code
6. 🚀 Redeploy to run the full app!
    """)
    st.stop()

# --- NORMAL APP CODE STARTS HERE ---
# Only runs when DEBUG_MODE = False

import PIL.Image
import os

st.set_page_config(page_title="Study Master Pro", layout="centered", page_icon="🎓")

# --- SUPABASE INIT ---
@st.cache_resource
def initialize_supabase():
    try:
        from supabase import create_client, Client
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase failed: {e}")
        st.info("💡 Turn on DEBUG_MODE in code to check secrets")
        return None

# --- GEMINI INIT ---
@st.cache_resource
def initialize_gemini():
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("GOOGLE_API_KEY not in secrets!")
            return None
        
        api_key = st.secrets["GOOGLE_API_KEY"].strip()
        
        if not api_key or len(api_key) < 20:
            st.error("API key invalid!")
            return None
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        st.info("🔍 Looking for available AI models...")
        
        models_to_try = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro",
        ]
        
        for model_name in models_to_try:
            try:
                st.info(f"Testing: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say ready")
                if response.text:
                    st.success(f"🎉 CONNECTED: {model_name}")
                    return model
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    st.warning(f"⚠️ {model_name} rate limited")
                continue
        
        st.error("All models unavailable!")
        return None
        
    except Exception as e:
        st.error(f"Fatal error: {e}")
        return None

# --- SAFE AI CALL ---
def safe_ai_call(model, prompt, max_retries=3, use_image=None):
    if not model:
        return None, "AI model not initialized"
    
    for attempt in range(max_retries):
        try:
            if use_image:
                response = model.generate_content([prompt, use_image])
            else:
                response = model.generate_content(prompt)
            
            if response and response.text:
                return response.text, None
            else:
                return None, "Empty response from AI"
                
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "quota" in error_str.lower():
                return None, f"⚠️ **Rate Limit Reached!**\n\nGoogle's free tier: 20 requests/day.\n\n**Options:**\n1. ⏰ Wait 60 seconds\n2. 🔑 Upgrade API plan\n3. 📅 Use Schedule Planner"
            
            if attempt < max_retries - 1:
                time_module.sleep((attempt + 1) * 2)
            else:
                return None, f"Error: {error_str}"
    
    return None, "Unknown error"

# Initialize
supabase = initialize_supabase()
model = initialize_gemini()

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_calls_today" not in st.session_state:
    st.session_state.api_calls_today = 0
if "last_reset" not in st.session_state:
    st.session_state.last_reset = datetime.now().date()

# --- HELPER FUNCTIONS ---
def get_daily_usage():
    if st.session_state.last_reset != datetime.now().date():
        st.session_state.api_calls_today = 0
        st.session_state.last_reset = datetime.now().date()
    
    if not supabase or not st.session_state.user:
        return st.session_state.api_calls_today
    
    try:
        time_threshold = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq(
            "user_id", st.session_state.user.id
        ).gte("created_at", time_threshold).execute()
        return res.count if res.count else 0
    except:
        return st.session_state.api_calls_today

def increment_usage():
    st.session_state.api_calls_today += 1

def load_chat_history():
    if not supabase or not st.session_state.user:
        return []
    try:
        res = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(20).execute()
        return list(reversed(res.data)) if res.data else []
    except:
        return []

def save_chat_message(question, answer):
    if not supabase or not st.session_state.user:
        return False
    try:
        supabase.table("history").insert({
            "user_id": st.session_state.user.id,
            "question": question,
            "answer": answer,
            "created_at": datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

def clear_chat_history():
    if not supabase or not st.session_state.user:
        return False
    try:
        supabase.table("history").delete().eq(
            "user_id", st.session_state.user.id
        ).execute()
        st.session_state.chat_history = []
        return True
    except:
        return False

# --- LOGIN SCREEN ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💬 **AI Chat**\nAsk anything!")
    with col2:
        st.info("📝 **Quiz Gen**\nCustom quizzes")
    with col3:
        st.info("📅 **Planner**\nStudy schedules")
    
    if not supabase:
        st.error("Connection failed. Check Supabase settings.")
        st.info("💡 Turn on DEBUG_MODE in code to diagnose")
        return
    
    tab1, tab2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    
    with tab1:
        st.write("### Welcome Back!")
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("🚀 Log In", use_container_width=True, type="primary"):
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email, 
                        "password": password
                    })
                    st.session_state.user = res.user
                    st.success("✅ Logged in!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")
            else:
                st.error("Please enter email and password")
    
    with tab2:
        st.write("### Create Your Account")
        new_email = st.text_input("Email", key="s_email")
        new_pass = st.text_input("Password (min 6 chars)", type="password", key="s_pass")
        confirm = st.text_input("Confirm Password", type="password", key="s_confirm")
        
        if st.button("🎉 Create Account", use_container_width=True, type="primary"):
            if not new_email or not new_pass:
                st.error("Fill all fields")
            elif len(new_pass) < 6:
                st.error("Password too short")
            elif new_pass != confirm:
                st.error("Passwords don't match")
            else:
                try:
                    res = supabase.auth.sign_up({
                        "email": new_email, 
                        "password": new_pass
                    })
                    if res.user:
                        st.session_state.user = res.user
                        st.success("✅ Account created!")
                        st.balloons()
                        time_module.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# --- MAIN APP ---
if st.session_state.user:
    if not model:
        st.warning("⚠️ AI unavailable")
        st.info("💡 You can still use Schedule Planner!")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master Pro")
    st.sidebar.write(f"👋 {st.session_state.user.email.split('@')[0]}")
    
    # Premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("⭐ Premium"):
            code = st.text_input("Code", type="password", key="prem")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium activated!")
                    st.balloons()
                    st.rerun()
    else:
        st.sidebar.success("⭐ Premium Member")
    
    # Usage
    usage = get_daily_usage()
    api_calls = st.session_state.api_calls_today
    limit = 250 if st.session_state.is_premium else 50
    
    st.sidebar.metric("Usage", f"{usage}/{limit}")
    st.sidebar.caption(f"🤖 API: {api_calls}/20")
    
    if api_calls >= 18:
        st.sidebar.warning("⚠️ API limit close!")
    
    # Menu
    menu = st.sidebar.radio("📚 Menu", [
        "💬 Chat", 
        "📝 Quiz", 
        "📁 Image", 
        "🎯 Tutor"
    ])
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.user = None
        st.session_state.chat_history = []
        st.rerun()
    
    # Features
    if menu == "💬 Chat":
        st.subheader("💬 AI Chat")
        
        if api_calls >= 15:
            st.warning(f"⚠️ API: {api_calls}/20 calls used")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col2:
            if st.button("📜 Load"):
                st.session_state.chat_history = load_chat_history()
                st.success("Loaded!")
        with col3:
            if st.button("🗑️ Clear"):
                if clear_chat_history():
                    st.success("Cleared!")
                    st.rerun()
        
        st.markdown("---")
        
        for msg in st.session_state.chat_history:
            with st.chat_message("user"):
                st.write(msg.get("question", ""))
            with st.chat_message("assistant"):
                st.write(msg.get("answer", ""))
        
        q = st.chat_input("Ask anything...")
        
        if q:
            with st.chat_message("user"):
                st.write(q)
            
            with st.spinner("Thinking..."):
                response_text, error = safe_ai_call(model, q)
            
            if response_text:
                with st.chat_message("assistant"):
                    st.write(response_text)
                
                increment_usage()
                save_chat_message(q, response_text)
                st.session_state.chat_history.append({
                    "question": q,
                    "answer": response_text,
                    "created_at": datetime.now().isoformat()
                })
            else:
                st.error(error)
    
    elif menu == "📝 Quiz":
        st.subheader("📝 Quiz Generator")
        
        topic = st.text_input("Topic:")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"])
        with col2:
            num = st.slider("Questions:", 3, 10, 5)
        
        if st.button("🎯 Generate", type="primary"):
            if not topic:
                st.error("Enter a topic!")
            else:
                prompt = f"""Create {num} MCQs about {topic} ({difficulty}).

Format:
Q1: [question]
A) [option]
B) [option]
C) [option]
D) [option]

Answer Key:
1. [letter]
etc."""
                
                with st.spinner("Creating..."):
                    response_text, error = safe_ai_call(model, prompt)
                
                if response_text:
                    st.markdown("---")
                    st.markdown(response_text)
                    st.download_button("📥 Download", response_text, f"quiz_{topic}.txt")
                    increment_usage()
                else:
                    st.error(error)
    
    elif menu == "📁 Image":
        st.subheader("📁 Image Analysis")
        
        file = st.file_uploader("Upload:", type=['jpg', 'png', 'jpeg'])
        
        if file:
            img = PIL.Image.open(file)
            st.image(img, width=400)
            
            if st.button("🔍 Analyze", type="primary"):
                prompt = "Analyze this study material: Summary, Key concepts, Study tips, Practice questions"
                
                with st.spinner("Analyzing..."):
                    response_text, error = safe_ai_call(model, prompt, use_image=img)
                
                if response_text:
                    st.markdown("---")
                    st.markdown(response_text)
                    increment_usage()
                else:
                    st.error(error)
    
    elif menu == "🎯 Tutor":
        st.subheader("🎯 Socratic Tutor")
        
        problem = st.text_area("Your problem:", height=150)
        
        if st.button("🚀 Start", type="primary"):
            if not problem:
                st.error("Describe your problem!")
            else:
                prompt = f"""Socratic tutor for: "{problem}"

Ask 3-4 guiding questions. Don't give the answer.
Start: "Let me help you think..."
"""
                
                with st.spinner("Thinking..."):
                    response_text, error = safe_ai_call(model, prompt)
                
                if response_text:
                    st.markdown("---")
                    st.markdown(response_text)
                    increment_usage()
                else:
                    st.error(error)

else:
    login_screen()
