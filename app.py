import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta, time as dt_time
import time
import base64
import io
import json
import re
from PIL import Image
import hashlib

# ==================== CORE SETUP ====================

st.set_page_config(
    page_title="Study Master Infinity - Free AI Study Assistant",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/yourrepo',
        'Report a bug': 'https://github.com/yourrepo/issues',
        'About': '# Study Master Infinity\nFree AI-powered study assistant!'
    }
)

# Google Search Console Verification + SEO Meta Tags
st.markdown("""
<head>
    <meta name="google-site-verification" content="ThWp6_7rt4Q973HycJ07l-jYZ0o55s8f0Em28jBBNoU" />
    <meta name="description" content="Study Master Infinity - Free AI study assistant with chat, quiz generator, teacher mode, image analysis, flashcards and study planner. Powered by Groq AI. Perfect for students worldwide!">
    <meta name="keywords" content="study master infinity, study master, AI study tool, free study assistant, AI tutor, quiz generator, study planner, groq ai, free education tool, student helper, exam preparation">
    <meta name="author" content="Aarya">
    <meta name="robots" content="index, follow">
    <meta property="og:title" content="Study Master Infinity - Free AI Study Assistant">
    <meta property="og:description" content="Chat with AI, generate quizzes, get tested and graded, analyze images, create flashcards - all free!">
    <meta property="og:type" content="website">
    <meta property="og:locale" content="en_US">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Study Master Infinity">
    <meta name="twitter:description" content="Free AI Study Assistant - Chat, Quiz, Test & Grade!">
</head>
""", unsafe_allow_html=True)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        padding: 1rem;
    }
    .feature-box {
        padding: 1rem;
        border-radius: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin: 0.5rem 0;
    }
    .xp-badge {
        background: gold;
        color: black;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==================== API INITIALIZATION ====================

@st.cache_resource
def initialize_supabase():
    """Initialize Supabase client with error handling"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        client = create_client(url, key)
        return client, None
    except Exception as e:
        return None, str(e)

@st.cache_resource
def initialize_groq():
    """Initialize Groq client with error handling"""
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        client = Groq(api_key=api_key)
        # Test connection
        client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        return client, None
    except Exception as e:
        return None, str(e)

# Initialize clients
supabase, supabase_error = initialize_supabase()
groq_client, groq_error = initialize_groq()

# Display initialization errors if any
if supabase_error:
    st.error(f"⚠️ Supabase Error: {supabase_error}")
    st.info("Add Supabase credentials to Streamlit Secrets")
    st.stop()

if groq_error:
    st.error(f"⚠️ Groq Error: {groq_error}")
    st.info("Add GROQ_API_KEY to Streamlit Secrets")
    st.stop()

# ==================== SESSION STATE INITIALIZATION ====================

def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'user': None,
        'is_guest': False,  # Track if user is guest
        'user_data': {},
        'selected_menu': "🏠 Home",  # Track menu selection
        'chat_messages': [],
        'test_active': False,
        'test_questions': [],
        'test_answers': {},
        'test_submitted': False,
        'api_calls_today': 0,
        'last_reset': datetime.now().date(),
        'current_streak': 0,
        'achievements': [],
        'study_timer_active': False,
        'study_timer_start': None,
        'total_study_time': 0,
        'notes': [],
        'bookmarks': [],
        'dark_mode': False,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# ==================== UTILITY FUNCTIONS ====================

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    return bool(re.match(r'^[\w\-]{3,20}$', username, re.UNICODE))

def get_daily_usage():
    """Get user's daily API usage"""
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
    """Increment daily API call counter"""
    st.session_state.api_calls_today += 1

def award_xp(amount, reason=""):
    """Award XP to user and update profile"""
    if not supabase or not st.session_state.user:
        return False
    
    try:
        current_xp = st.session_state.user_data.get('xp', 0)
        new_xp = current_xp + amount
        
        supabase.table("profiles").update({
            "xp": new_xp
        }).eq("id", st.session_state.user.id).execute()
        
        st.session_state.user_data['xp'] = new_xp
        
        # Check for level up
        old_level = current_xp // 100 + 1
        new_level = new_xp // 100 + 1
        
        if new_level > old_level:
            st.balloons()
            st.success(f"🎉 LEVEL UP! You're now Level {new_level}!")
        
        return True
    except Exception as e:
        st.error(f"XP error: {e}")
        return False

def check_achievement(achievement_type):
    """Check and award achievements"""
    achievements_map = {
        'first_chat': {'name': '💬 First Chat', 'xp': 50},
        'quiz_master': {'name': '📝 Quiz Master', 'xp': 100},
        'test_ace': {'name': '🏆 Test Ace', 'xp': 150},
        'study_streak': {'name': '🔥 7-Day Streak', 'xp': 200},
        'knowledge_seeker': {'name': '🧠 100 Questions', 'xp': 300},
    }
    
    if achievement_type in achievements_map:
        achievement = achievements_map[achievement_type]
        if achievement_type not in st.session_state.achievements:
            st.session_state.achievements.append(achievement_type)
            award_xp(achievement['xp'], f"Achievement: {achievement['name']}")
            st.success(f"🏅 Achievement Unlocked: {achievement['name']} (+{achievement['xp']} XP)")

# ==================== AI HELPER FUNCTIONS ====================

VISION_MODELS = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
]

def safe_ai_call(prompt, system_role="Expert Study Assistant", include_memory=True, model="llama-3.3-70b-versatile"):
    """
    Safe AI call with error handling and retry logic
    """
    if not groq_client:
        return None, "AI client not initialized"
    
    try:
        messages = []
        
        # Add memory if requested
        if include_memory and st.session_state.chat_messages:
            for msg in st.session_state.chat_messages[-10:]:  # Last 10 messages
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # System message
        messages.insert(0, {
            "role": "system",
            "content": f"{system_role}. Be helpful, clear, and educational."
        })
        
        # Current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Call Groq
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content, None
        
    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str.lower() or "429" in error_str:
            return None, "⚠️ Rate limit reached. Please wait a moment and try again."
        return None, f"Error: {error_str}"

def analyze_image_with_ai(image_file, prompt):
    """Analyze image using Groq vision model"""
    try:
        # Convert image to base64
        img = Image.open(image_file)
        
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        image_bytes = buffer.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        
        # Try vision models in order; Groq retires models often, so keep a fallback list
        candidates = VISION_MODELS
        try:
            override = st.secrets.get("GROQ_VISION_MODEL")
            if override:
                candidates = [override] + [m for m in VISION_MODELS if m != override]
        except Exception:
            pass

        last_error = None
        for vision_model in candidates:
            try:
                response = groq_client.chat.completions.create(
                    model=vision_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                                {"type": "text", "text": prompt}
                            ]
                        }
                    ],
                    max_tokens=1500
                )
                return response.choices[0].message.content, None
            except Exception as e:
                last_error = str(e)
                if "decommissioned" in last_error or "model_not_found" in last_error or "does not exist" in last_error:
                    continue  # try next model
                break  # real error (rate limit, bad image, etc.) - don't hide it

        return None, f"Vision error: {last_error}"

    except Exception as e:
        return None, str(e)

# ==================== DATABASE FUNCTIONS ====================

def save_chat_message(role, content):
    """Save chat message to database - only for logged-in users"""
    # Don't save for guests
    if st.session_state.get('is_guest', False):
        return True  # Return True so app doesn't break
    
    if not supabase or not st.session_state.user:
        return False
    
    try:
        supabase.table("history").insert({
            "user_id": st.session_state.user.id,
            "role": role,
            "content": content,
            "created_at": datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

def load_chat_history():
    """Load recent chat history - only for logged-in users"""
    # Guests don't have history
    if st.session_state.get('is_guest', False):
        return []
    
    if not supabase or not st.session_state.user:
        return []
    
    try:
        res = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=False).limit(50).execute()
        
        return res.data if res.data else []
    except:
        return []

def clear_chat_history():
    """Clear all chat history"""
    # For guests, just clear session
    if st.session_state.get('is_guest', False):
        st.session_state.chat_messages = []
        return True
    
    if not supabase or not st.session_state.user:
        return False
    
    try:
        supabase.table("history").delete().eq(
            "user_id", st.session_state.user.id
        ).execute()
        st.session_state.chat_messages = []
        return True
    except:
        return False

def save_note(title, content, tags=""):
    """Save study note - only for logged-in users"""
    # Guests can't save notes
    if st.session_state.get('is_guest', False):
        return False
    
    if not supabase or not st.session_state.user:
        return False
    
    try:
        supabase.table("notes").insert({
            "user_id": st.session_state.user.id,
            "title": title,
            "content": content,
            "tags": tags,
            "created_at": datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

def load_notes():
    """Load user's notes - only for logged-in users"""
    # Guests don't have notes
    if st.session_state.get('is_guest', False):
        return []
    
    if not supabase or not st.session_state.user:
        return []
    
    try:
        res = supabase.table("notes").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).execute()
        return res.data if res.data else []
    except:
        return []

def delete_note(note_id):
    """Delete a note"""
    if not supabase or st.session_state.get('is_guest', False):
        return False
    
    try:
        supabase.table("notes").delete().eq("id", note_id).execute()
        return True
    except:
        return False

# ==================== AUTHENTICATION ====================

def login_screen():
    """Beautiful login/signup screen with guest access option"""
    
    # Header
    st.markdown('<h1 class="main-header">🎓 Study Master Infinity</h1>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #666;'>Your Ultimate AI-Powered Study Companion</p>", unsafe_allow_html=True)
    
    # Feature showcase
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info("💬 **Smart Chat**\nAI with memory")
    with col2:
        st.info("👨‍🏫 **Teacher Mode**\nTests & grading")
    with col3:
        st.info("📸 **Image Analysis**\nSnap & learn")
    with col4:
        st.info("📊 **Progress Tracking**\nXP & levels")
    
    st.markdown("---")
    
    # Guest access button (prominent)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Try as Guest (No Login Required)", use_container_width=True, type="primary"):
            # Set guest user
            st.session_state.user = {"id": "guest", "email": "guest@studymaster.app"}
            st.session_state.is_guest = True
            st.success("✅ Welcome, Guest! Your session won't be saved.")
            time.sleep(0.5)
            st.rerun()
    
    st.markdown("---")
    st.write("**Or login to save your progress:**")
    
    # Login/Signup tabs
    tab1, tab2 = st.tabs(["🔑 Login", "✨ Create Account"])
    
    # LOGIN TAB
    with tab1:
        st.write("### Welcome Back!")
        
        with st.form("login_form"):
            login_email = st.text_input("📧 Email", placeholder="your@email.com")
            login_pass = st.text_input("🔒 Password", type="password", placeholder="Enter password")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                submit = st.form_submit_button("🚀 Log In", use_container_width=True, type="primary")
            
            if submit:
                if not login_email or not login_pass:
                    st.error("❌ Please enter both email and password")
                elif not validate_email(login_email):
                    st.error("❌ Invalid email format")
                else:
                    try:
                        with st.spinner("🔐 Logging in..."):
                            res = supabase.auth.sign_in_with_password({
                                "email": login_email,
                                "password": login_pass
                            })
                            st.session_state.user = res.user
                            st.session_state.is_guest = False
                            st.success("✅ Login successful!")
                            st.balloons()
                            time.sleep(0.5)
                            st.rerun()
                    except Exception as e:
                        error_msg = str(e)
                        if "Invalid login credentials" in error_msg:
                            st.error("❌ Invalid email or password!")
                        elif "Email not confirmed" in error_msg:
                            st.error("❌ Please verify your email first!")
                        else:
                            st.error(f"❌ Login failed: {error_msg}")
    
    # SIGNUP TAB
    with tab2:
        st.write("### Join Study Master Infinity!")
        st.success("🎁 Free forever • Save your progress")
        
        with st.form("signup_form"):
            signup_email = st.text_input("📧 Email Address", placeholder="your@email.com")
            
            col1, col2 = st.columns(2)
            with col1:
                signup_pass = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters")
            with col2:
                confirm_pass = st.text_input("🔒 Confirm Password", type="password", placeholder="Re-enter password")
            
            agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
            
            submit = st.form_submit_button("🎉 Create Account", use_container_width=True, type="primary")
            
            if submit:
                if not signup_email or not signup_pass:
                    st.error("❌ Please fill in all fields")
                elif not validate_email(signup_email):
                    st.error("❌ Invalid email format")
                elif len(signup_pass) < 6:
                    st.error("❌ Password must be at least 6 characters")
                elif signup_pass != confirm_pass:
                    st.error("❌ Passwords don't match!")
                elif not agree_terms:
                    st.error("❌ Please accept the Terms of Service")
                
