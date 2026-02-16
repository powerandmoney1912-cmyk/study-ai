import streamlit as st
from datetime import datetime, timedelta, time
import json
import time as time_module

# ============================================================================
# 🎛️ CONTROL PANEL - CHANGE THESE TO SWITCH MODES
# ============================================================================

MODE = "DEBUG"  # Options: "TEST_KEY", "DEBUG", "APP"

# MODE = "TEST_KEY"  → Test your Google API key
# MODE = "DEBUG"     → Debug your Streamlit secrets
# MODE = "APP"       → Run the full Study Master Pro app

# ============================================================================
# 🔑 GOOGLE API KEY TESTER
# ============================================================================

if MODE == "TEST_KEY":
    st.title("🔑 Google API Key Tester")
    st.write("## Test Your Google API Key")
    
    api_key_input = st.text_input("Paste your Google API Key here:", type="password")
    
    if api_key_input:
        st.write("### Running Tests...")
        
        # Test 1: Basic Format
        st.write("**Test 1: Basic Format**")
        if api_key_input.startswith("AIza"):
            st.success("✅ Key starts with 'AIza' - Good!")
        else:
            st.error(f"❌ Key should start with 'AIza', but starts with: {api_key_input[:10]}")
        
        if len(api_key_input) == 39:
            st.success(f"✅ Key length is 39 characters - Perfect!")
        else:
            st.warning(f"⚠️ Key length is {len(api_key_input)} chars (usually 39)")
        
        if " " in api_key_input:
            st.error("❌ Key contains SPACES! Remove all spaces!")
        else:
            st.success("✅ No spaces found")
        
        if "\n" in api_key_input or "\t" in api_key_input:
            st.error("❌ Key contains hidden characters (newlines/tabs)!")
        else:
            st.success("✅ No hidden characters")
        
        # Test 2: API Connection
        st.write("---")
        st.write("**Test 2: API Connection Test**")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key_input.strip())
            
            st.info("🔄 Testing connection to Google AI...")
            
            try:
                models = list(genai.list_models())
                st.success(f"✅ Connected! Found {len(models)} models available")
                
                with st.expander("📋 Available models"):
                    for m in models:
                        if 'generateContent' in m.supported_generation_methods:
                            st.write(f"✅ {m.name}")
                
                # Test actual generation
                st.write("---")
                st.write("**Test 3: Generation Test**")
                
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content("Say 'API key working!'")
                    
                    if response and response.text:
                        st.success("✅ API KEY IS WORKING PERFECTLY!")
                        st.balloons()
                        st.success(f"AI Response: {response.text}")
                        
                        st.write("---")
                        st.write("## ✅ YOUR KEY IS VALID!")
                        st.info("Copy this EXACT key to your Streamlit secrets:")
                        st.code(api_key_input.strip())
                        
                        st.write("**Next steps:**")
                        st.write("1. Change MODE = 'DEBUG' in code (line 13)")
                        st.write("2. Add this key to your secrets")
                        st.write("3. Test secrets with DEBUG mode")
                    else:
                        st.error("❌ Got empty response")
                        
                except Exception as e:
                    error_msg = str(e)
                    
                    if "429" in error_msg or "quota" in error_msg.lower():
                        st.error("❌ RATE LIMIT!")
                        st.warning("Your key is VALID but you've hit the 20 requests/day limit!")
                        st.info("✅ Your key works! Just wait 24 hours or upgrade")
                    elif "API_KEY_INVALID" in error_msg:
                        st.error("❌ API Key is INVALID!")
                        st.write("**Create NEW key at:**")
                        st.code("https://makersuite.google.com/app/apikey")
                    else:
                        st.error(f"❌ Error: {error_msg}")
                        
            except Exception as e:
                st.error(f"❌ Failed to connect: {str(e)}")
                st.info("Create fresh key at: https://makersuite.google.com/app/apikey")
            
        except ImportError:
            st.error("❌ google-generativeai not installed!")
            st.code("pip install google-generativeai")
    
    st.write("---")
    st.write("## 📍 Where to Get Your Key")
    st.success("""
✅ CORRECT: https://makersuite.google.com/app/apikey
❌ WRONG: https://console.cloud.google.com
    """)
    
    st.write("## 🎯 Next Step")
    st.info("Once key test passes, change MODE = 'DEBUG' in code to test your secrets!")
    
    st.stop()

# ============================================================================
# 🔍 SECRETS DEBUGGER
# ============================================================================

if MODE == "DEBUG":
    st.title("🔍 Secrets Debug Tool")
    st.write("## Testing Your Streamlit Secrets")
    st.warning("⚠️ MODE is set to DEBUG. Change to 'APP' after fixing secrets!")
    
    # Test 1: Secrets exist
    st.write("### Test 1: Do secrets exist?")
    try:
        all_secrets = st.secrets
        st.success(f"✅ Secrets found! Top-level keys: {list(all_secrets.keys())}")
    except Exception as e:
        st.error(f"❌ No secrets: {e}")
        st.stop()
    
    # Test 2: Supabase
    st.write("### Test 2: Supabase Section")
    supabase_ok = False
    try:
        if "supabase" in st.secrets:
            st.success("✅ 'supabase' section exists")
            st.write(f"Keys in supabase: {list(st.secrets['supabase'].keys())}")
            
            # Check URL
            if "url" in st.secrets["supabase"]:
                url = st.secrets["supabase"]["url"]
                st.success(f"✅ URL found: {url[:40]}...")
                
                if url.startswith("https://") and "supabase.co" in url:
                    st.success("✅ URL format correct!")
                else:
                    st.error(f"❌ URL should be: https://xxxxx.supabase.co")
                    st.error(f"Your URL: {url}")
            else:
                st.error("❌ 'url' not found under [supabase]")
            
            # Check key
            if "key" in st.secrets["supabase"]:
                key = st.secrets["supabase"]["key"]
                st.success(f"✅ Key found: {key[:40]}...")
                
                if len(key) > 100:
                    st.success(f"✅ Key length good! ({len(key)} chars)")
                    supabase_ok = True
                else:
                    st.error(f"❌ Key too short: {len(key)} chars")
            else:
                st.error("❌ 'key' not found under [supabase]")
        else:
            st.error("❌ 'supabase' section not found!")
            st.write(f"Available: {list(st.secrets.keys())}")
    except Exception as e:
        st.error(f"❌ Supabase error: {e}")
    
    # Test 3: Google API Key
    st.write("### Test 3: Google API Key")
    google_ok = False
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success(f"✅ GOOGLE_API_KEY found: {api_key[:20]}...")
            
            if api_key.startswith("AIza"):
                st.success("✅ Key format correct!")
            else:
                st.error(f"❌ Should start with 'AIza', starts with: {api_key[:10]}")
            
            if len(api_key) == 39:
                st.success("✅ Length correct (39 chars)")
                google_ok = True
            else:
                st.warning(f"⚠️ Length is {len(api_key)} (usually 39)")
        else:
            st.error("❌ 'GOOGLE_API_KEY' not found!")
            st.write(f"Available: {list(st.secrets.keys())}")
    except Exception as e:
        st.error(f"❌ Google key error: {e}")
    
    # Test 4: Test Supabase Connection
    if supabase_ok:
        st.write("### Test 4: Supabase Connection")
        try:
            from supabase import create_client
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            client = create_client(url, key)
            st.success("✅ Supabase client created successfully!")
        except Exception as e:
            st.error(f"❌ Supabase connection failed: {e}")
    
    # Test 5: Test Google API
    if google_ok:
        st.write("### Test 5: Google API Connection")
        try:
            import google.generativeai as genai
            api_key = st.secrets["GOOGLE_API_KEY"]
            genai.configure(api_key=api_key.strip())
            
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content("Say ready")
            if response.text:
                st.success("✅ Google API working!")
                st.success(f"Response: {response.text}")
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                st.warning("⚠️ Rate limit hit, but key IS valid!")
            else:
                st.error(f"❌ Google API error: {error_str}")
    
    # Summary
    st.write("---")
    st.write("## 📋 Summary")
    
    if supabase_ok and google_ok:
        st.success("🎉 ALL TESTS PASSED!")
        st.balloons()
        st.info("""
**Next steps:**
1. Change MODE = 'APP' in code (line 13)
2. Redeploy your app
3. Enjoy Study Master Pro!
        """)
    else:
        st.error("❌ Some tests failed - fix secrets below")
    
    st.write("## 🔧 Your Secrets Should Look Like:")
    st.code("""[supabase]
url = "https://xxxxx.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

GOOGLE_API_KEY = "AIzaSyAaBbCcDdEeFfGgHhIiJjKk..."
""", language="toml")
    
    st.stop()

# ============================================================================
# 📱 FULL APP MODE
# ============================================================================

if MODE != "APP":
    st.error("⚠️ MODE is not set to 'APP'")
    st.info("Change MODE = 'APP' in line 13 to run the full app")
    st.stop()

# --- APP CODE STARTS HERE ---
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
        st.info("💡 Change MODE to 'DEBUG' in code to diagnose")
        return None

# --- GEMINI INIT ---
@st.cache_resource
def initialize_gemini():
    try:
        if "GOOGLE_API_KEY" not in st.secrets:
            st.error("GOOGLE_API_KEY not in secrets!")
            st.info("💡 Change MODE to 'DEBUG' in code")
            return None
        
        api_key = st.secrets["GOOGLE_API_KEY"].strip()
        
        if not api_key or len(api_key) < 20:
            st.error("API key invalid!")
            return None
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        st.info("🔍 Connecting to AI...")
        
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
                    st.success(f"🎉 Connected: {model_name}")
                    return model
            except Exception as e:
                if "429" in str(e):
                    st.warning(f"⚠️ {model_name} rate limited")
                continue
        
        st.error("All models unavailable!")
        return None
        
    except Exception as e:
        st.error(f"Error: {e}")
        st.info("💡 Change MODE to 'TEST_KEY' to test your API key")
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
                return None, "Empty response"
                
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "quota" in error_str.lower():
                return None, f"⚠️ **Rate Limit!**\n\nGoogle's free tier: 20/day.\n\n**Options:**\n1. ⏰ Wait 60s\n2. 🔑 Upgrade API\n3. 📅 Use Schedule Planner"
            
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
        st.info("🎯 **Tutor**\nSocratic learning")
    
    if not supabase:
        st.error("Connection failed")
        st.info("💡 Change MODE to 'DEBUG' to diagnose")
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
                    st.error(f"❌ Failed: {str(e)}")
            else:
                st.error("Enter email and password")
    
    with tab2:
        st.write("### Create Account")
        new_email = st.text_input("Email", key="s_email")
        new_pass = st.text_input("Password (min 6)", type="password", key="s_pass")
        confirm = st.text_input("Confirm Password", type="password", key="s_confirm")
        
        if st.button("🎉 Create", use_container_width=True, type="primary"):
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
                        st.success("✅ Created!")
                        st.balloons()
                        time_module.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

# --- MAIN APP ---
if st.session_state.user:
    if not model:
        st.warning("⚠️ AI unavailable")
        st.info("Change MODE to 'DEBUG' or 'TEST_KEY' to diagnose")
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
                    st.success("Premium!")
                    st.balloons()
                    st.rerun()
    else:
        st.sidebar.success("⭐ Premium")
    
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
            st.warning(f"⚠️ API: {api_calls}/20")
        
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
                st.error("Enter topic!")
            else:
                prompt = f"""Create {num} MCQs about {topic} ({difficulty}).

Format:
Q1: [question]
A) [option]
B) [option]
C) [option]
D) [option]

Answer Key:
1. [letter]"""
                
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
                prompt = "Analyze this study material: Summary, Key concepts, Study tips, Questions"
                
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
                st.error("Describe problem!")
            else:
                prompt = f"""Socratic tutor: "{problem}"

Ask 3-4 guiding questions. Don't give answer.
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
