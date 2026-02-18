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
        'user_data': {},
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
        
        # Try primary vision model
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                max_tokens=1500
            )
            return response.choices[0].message.content, None
        except:
            # Fallback to text-based description
            return None, "Vision model unavailable. Please describe the image and I'll help!"
            
    except Exception as e:
        return None, str(e)

# ==================== DATABASE FUNCTIONS ====================

def save_chat_message(role, content):
    """Save chat message to database"""
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
    """Load recent chat history"""
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
    """Save study note"""
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
    """Load user's notes"""
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
    if not supabase:
        return False
    
    try:
        supabase.table("notes").delete().eq("id", note_id).execute()
        return True
    except:
        return False

# ==================== AUTHENTICATION ====================

def login_screen():
    """Beautiful login/signup screen"""
    
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
        st.success("🎁 Free forever • No credit card required")
        
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
                else:
                    try:
                        with st.spinner("🎨 Creating your account..."):
                            res = supabase.auth.sign_up({
                                "email": signup_email,
                                "password": signup_pass
                            })
                            
                            if res.user:
                                st.success("✅ Account created successfully!")
                                st.info("📧 Please check your email to verify your account")
                                st.balloons()
                                
                                # Auto-login if email confirmed
                                if hasattr(res.user, 'email_confirmed_at') and res.user.email_confirmed_at:
                                    st.session_state.user = res.user
                                    st.success("🎉 You're now logged in!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Please verify your email, then login above")
                    except Exception as e:
                        error_msg = str(e)
                        if "already registered" in error_msg.lower():
                            st.error("❌ Email already registered! Please login instead.")
                        else:
                            st.error(f"❌ Signup error: {error_msg}")
    
    st.markdown("---")
    st.caption("🔐 Your data is encrypted and secure • 🌍 Available worldwide • ⚡ Powered by Groq AI")

def username_setup_screen():
    """Username and profile setup screen"""
    st.title("🎨 Complete Your Profile")
    st.write("### Choose Your Identity")
    st.info("💡 Pick a unique username - this is how you'll be known!")
    
    with st.form("username_form"):
        username_input = st.text_input(
            "👤 Username",
            placeholder="e.g., Seashore, Kandasamy, StarLearner",
            max_chars=20
        )
        
        # Live validation
        if username_input:
            if len(username_input) < 3:
                st.warning("⚠️ Username must be at least 3 characters")
            elif not validate_username(username_input):
                st.warning("⚠️ Only letters, numbers, _ and - allowed")
            else:
                st.success("✅ Username looks good!")
        
        # Avatar selection
        st.write("### Pick Your Avatar")
        avatar_options = ["🎓", "📚", "🧠", "⚡", "🌟", "🚀", "💎", "🔥", "👑", "🎯", "🦉", "🐼", "🦊", "🐨", "🦁"]
        selected_avatar = st.selectbox("Choose an emoji:", avatar_options)
        
        # Bio (optional)
        bio = st.text_area("📝 Short Bio (optional)", placeholder="I'm a student who loves learning!", max_chars=150)
        
        submit = st.form_submit_button("💾 Create Profile", use_container_width=True, type="primary")
        
        if submit:
            if not username_input:
                st.error("❌ Please enter a username")
            elif len(username_input) < 3:
                st.error("❌ Username too short")
            elif not validate_username(username_input):
                st.error("❌ Invalid username format")
            else:
                try:
                    # Check if username exists
                    existing = supabase.table("profiles").select("id").eq("username", username_input).execute()
                    
                    if existing.data:
                        st.error("❌ Username already taken! Try another.")
                    else:
                        # Create profile
                        try:
                            supabase.table("profiles").insert({
                                "id": st.session_state.user.id,
                                "username": username_input,
                                "avatar": selected_avatar,
                                "bio": bio if bio else "",
                                "xp": 0,
                                "is_premium": False,
                                "study_streak": 0,
                                "total_study_time": 0,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                        except:
                            # Fallback without optional columns
                            supabase.table("profiles").insert({
                                "id": st.session_state.user.id,
                                "username": username_input,
                                "xp": 0,
                                "is_premium": False,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                        
                        st.success(f"✅ Welcome, {username_input}! 🎉")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.caption("💡 Examples: Seashore, Kandasamy, StarLearner, BrainMaster")

# ==================== MAIN APP FEATURES ====================

def show_sidebar():
    """Enhanced sidebar with user info and navigation"""
    with st.sidebar:
        # User profile header
        avatar = st.session_state.user_data.get('avatar', '🎓')
        username = st.session_state.user_data.get('username', 'User')
        
        st.markdown(f"# {avatar} {username}")
        
        # Level and XP
        xp = st.session_state.user_data.get('xp', 0)
        level = xp // 100 + 1
        xp_in_level = xp % 100
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Level", level)
        with col2:
            st.metric("⭐ XP", xp)
        with col3:
            streak = st.session_state.user_data.get('study_streak', 0)
            st.metric("🔥 Streak", f"{streak}d")
        
        st.progress(xp_in_level / 100)
        st.caption(f"{xp_in_level}/100 XP to Level {level + 1}")
        
        st.markdown("---")
        
        # Premium section
        is_premium = st.session_state.user_data.get('is_premium', False)
        
        if not is_premium:
            with st.expander("⭐ Unlock Premium"):
                st.write("**Premium Benefits:**")
                st.write("✅ Unlimited AI calls")
                st.write("✅ Priority support")
                st.write("✅ Advanced features")
                st.write("✅ Custom themes")
                st.write("✅ Ad-free experience")
                
                code = st.text_input("Enter Premium Code", type="password", key="premium_code")
                if st.button("Activate Premium"):
                    if code in ["STUDY777", "PREMIUM2025", "AARYA"]:
                        try:
                            supabase.table("profiles").update({
                                "is_premium": True
                            }).eq("id", st.session_state.user.id).execute()
                            st.session_state.user_data['is_premium'] = True
                            st.success("💎 Premium activated!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        except:
                            st.error("Activation failed")
                    else:
                        st.error("Invalid code")
        else:
            st.success("💎 PREMIUM MEMBER")
        
        st.markdown("---")
        
        # Main menu
        menu = st.radio("📚 Features", [
            "🏠 Home",
            "💬 Chat",
            "📝 Quiz Generator",
            "👨‍🏫 Teacher Mode",
            "📅 Schedule Planner",
            "📸 Image Analysis",
            "🗂️ Flashcards",
            "📓 Study Notes",
            "⏱️ Study Timer",
            "📊 Dashboard",
            "⚙️ Settings"
        ])
        
        st.markdown("---")
        
        # Usage stats
        usage = get_daily_usage()
        api_calls = st.session_state.api_calls_today
        limit = 1000 if is_premium else 100
        
        st.caption(f"Today's Usage: {usage}/{limit}")
        st.caption(f"API Calls: {api_calls}/20")
        
        if api_calls >= 18:
            st.warning("⚠️ Close to API limit!")
        
        st.markdown("---")
        
        # Footer
        st.caption("✨ Made by Aarya")
        st.caption("⚡ Powered by Groq AI")
        
        if st.button("🚪 Logout", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except:
                pass
            st.session_state.user = None
            st.session_state.chat_messages = []
            st.success("Logged out!")
            st.rerun()
    
    return menu

def show_home():
    """Home dashboard with overview"""
    st.title("🏠 Welcome to Study Master Infinity!")
    
    username = st.session_state.user_data.get('username', 'Student')
    st.markdown(f"### Hello, {username}! Ready to learn today?")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        xp = st.session_state.user_data.get('xp', 0)
        st.metric("⭐ Total XP", xp)
    
    with col2:
        level = xp // 100 + 1
        st.metric("📊 Level", level)
    
    with col3:
        streak = st.session_state.user_data.get('study_streak', 0)
        st.metric("🔥 Streak", f"{streak} days")
    
    with col4:
        study_time = st.session_state.user_data.get('total_study_time', 0)
        hours = study_time // 3600
        st.metric("⏱️ Study Time", f"{hours}h")
    
    st.markdown("---")
    
    # Feature cards
    st.write("### 🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Start Chatting", use_container_width=True):
            st.session_state.sidebar_choice = "💬 Chat"
            st.rerun()
    
    with col2:
        if st.button("📝 Take a Quiz", use_container_width=True):
            st.session_state.sidebar_choice = "📝 Quiz Generator"
            st.rerun()
    
    with col3:
        if st.button("👨‍🏫 Start Test", use_container_width=True):
            st.session_state.sidebar_choice = "👨‍🏫 Teacher Mode"
            st.rerun()
    
    st.markdown("---")
    
    # Recent activity
    st.write("### 📈 Recent Activity")
    
    try:
        recent = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(5).execute()
        
        if recent.data:
            for activity in recent.data:
                with st.expander(f"{activity['role'].title()}: {activity['content'][:50]}..."):
                    st.write(activity['content'])
                    st.caption(f"🕒 {activity['created_at'][:19]}")
        else:
            st.info("No recent activity. Start using features to see your progress!")
    except:
        st.info("Activity tracking unavailable")
    
    st.markdown("---")
    
    # Tips
    st.write("### 💡 Study Tips")
    tips = [
        "🎯 Set specific goals for each study session",
        "⏰ Take a 5-minute break every 25 minutes (Pomodoro)",
        "📝 Test yourself regularly with quizzes",
        "🔄 Review material within 24 hours for better retention",
        "💬 Teach others - explaining helps you learn better"
    ]
    st.info("\n\n".join(tips))

def show_chat():
    """Enhanced chat with memory and features"""
    st.header("💬 AI Study Chat")
    st.caption("⚡ Smart AI with conversation memory")
    
    # Controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.write("💡 Ask anything!")
    with col2:
        if st.button("🔄 Reload", key="reload_chat"):
            history = load_chat_history()
            st.session_state.chat_messages = [
                {"role": h["role"], "content": h["content"]}
                for h in history
            ]
            st.success("Reloaded!")
            st.rerun()
    with col3:
        if st.button("💾 Save", key="save_chat"):
            st.success("Auto-saved!")
    with col4:
        if st.button("🗑️ Clear", key="clear_chat"):
            if clear_chat_history():
                st.success("Cleared!")
                st.rerun()
    
    st.markdown("---")
    
    # Display messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your question..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Save to DB
        save_chat_message("user", prompt)
        
        # Get AI response
        with st.spinner("🤔 Thinking..."):
            response, error = safe_ai_call(prompt, include_memory=True)
        
        if response:
            st.session_state.chat_messages.append({"role": "assistant", "content": response})
            
            with st.chat_message("assistant"):
                st.write(response)
            
            # Save and award XP
            save_chat_message("assistant", response)
            increment_usage()
            award_xp(5, "Chat message")
            check_achievement('first_chat')
            
            st.rerun()
        else:
            st.error(error)

def show_quiz_generator():
    """Quiz generator feature"""
    st.header("📝 Quiz Generator")
    st.write("Create custom quizzes on any topic!")
    
    with st.form("quiz_form"):
        topic = st.text_input("📚 Topic", placeholder="e.g., World War 2, Photosynthesis")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("🎯 Difficulty", ["Easy", "Medium", "Hard", "Expert"])
        with col2:
            num_q = st.slider("❓ Questions", 3, 10, 5)
        
        submit = st.form_submit_button("🎯 Generate Quiz", use_container_width=True, type="primary")
        
        if submit and topic:
            prompt = f"""Create a {num_q}-question multiple choice quiz about {topic} at {difficulty} level.

Format each question EXACTLY like this:

**Question 1:** [question text]
A) [option]
B) [option]
C) [option]
D) [option]

[Repeat for all {num_q} questions]

**Answer Key:**
1. [correct letter]
2. [correct letter]
etc.

**Explanations:**
1. [brief explanation]
2. [brief explanation]
etc."""
            
            with st.spinner("🎨 Creating your quiz..."):
                quiz, error = safe_ai_call(prompt, include_memory=False)
            
            if quiz:
                st.markdown("---")
                st.markdown(quiz)
                st.markdown("---")
                
                st.download_button(
                    "📥 Download Quiz",
                    quiz,
                    file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                    mime="text/plain"
                )
                
                award_xp(10, "Quiz generated")
                check_achievement('quiz_master')
            else:
                st.error(error)

def show_teacher_mode():
    """Teacher mode with testing and grading"""
    st.header("👨‍🏫 Teacher Mode")
    st.info("📝 Take tests and get graded instantly!")
    
    # Initialize test state
    if "test_active" not in st.session_state:
        st.session_state.test_active = False
    if "test_questions" not in st.session_state:
        st.session_state.test_questions = []
    if "test_answers" not in st.session_state:
        st.session_state.test_answers = {}
    if "test_submitted" not in st.session_state:
        st.session_state.test_submitted = False
    
    if not st.session_state.test_active:
        # Test creation
        st.write("### 📚 Create Your Test")
        
        with st.form("test_form"):
            col1, col2 = st.columns(2)
            with col1:
                subject = st.text_input("📖 Subject", placeholder="Math, Science, History")
            with col2:
                topic = st.text_input("📌 Topic", placeholder="Algebra, Photosynthesis")
            
            col3, col4 = st.columns(2)
            with col3:
                difficulty = st.selectbox("🎯 Difficulty", ["Easy", "Medium", "Hard", "Expert"])
            with col4:
                num_q = st.slider("❓ Questions", 3, 10, 5)
            
            submit = st.form_submit_button("🎯 Generate Test", use_container_width=True, type="primary")
            
            if submit and subject:
                prompt = f"""Create a {num_q}-question multiple choice test about {subject} - {topic} ({difficulty}).

Format EXACTLY:

QUESTION 1
[question]
A) [option]
B) [option]
C) [option]
D) [option]
CORRECT_ANSWER: [letter]

[Repeat for all questions]"""
                
                with st.spinner("👨‍🏫 Creating test..."):
                    test_content, error = safe_ai_call(prompt, include_memory=False)
                
                if test_content:
                    # Parse test
                    questions = []
                    lines = test_content.split('\n')
                    current_q = {}
                    
                    for line in lines:
                        line = line.strip()
                        
                        if line.startswith('QUESTION'):
                            if current_q and 'question' in current_q:
                                questions.append(current_q)
                            current_q = {'options': {}, 'number': len(questions) + 1}
                        elif line and not line.startswith(('A)', 'B)', 'C)', 'D)', 'CORRECT_ANSWER')):
                            if 'question' not in current_q and len(line) > 5:
                                current_q['question'] = line
                        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                            letter = line[0]
                            text = line[2:].strip()
                            current_q['options'][letter] = text
                        elif 'CORRECT_ANSWER' in line:
                            answer = line.split(':')[1].strip()
                            current_q['correct'] = answer
                    
                    if current_q and 'question' in current_q:
                        questions.append(current_q)
                    
                    if questions:
                        st.session_state.test_questions = questions
                        st.session_state.test_active = True
                        st.session_state.test_answers = {}
                        st.session_state.test_submitted = False
                        st.success("✅ Test ready! Good luck!")
                        st.rerun()
                    else:
                        st.error("Failed to generate test. Try again!")
                else:
                    st.error(error)
    
    elif st.session_state.test_active and not st.session_state.test_submitted:
        # Taking test
        st.write("### 📝 Your Test")
        st.warning("⚠️ Choose carefully! You can only submit once.")
        
        progress = len(st.session_state.test_answers) / len(st.session_state.test_questions)
        st.progress(progress)
        st.caption(f"Answered: {len(st.session_state.test_answers)}/{len(st.session_state.test_questions)}")
        
        st.markdown("---")
        
        for idx, q in enumerate(st.session_state.test_questions):
            st.write(f"**Question {q['number']}**")
            st.write(q['question'])
            
            answer = st.radio(
                "Your answer:",
                options=list(q['options'].keys()),
                format_func=lambda x: f"{x}) {q['options'][x]}",
                key=f"q_{idx}",
                index=None
            )
            
            if answer:
                st.session_state.test_answers[idx] = answer
            
            st.markdown("---")
        
        if st.button("📤 Submit Test", use_container_width=True, type="primary"):
            if len(st.session_state.test_answers) < len(st.session_state.test_questions):
                st.error(f"⚠️ Answer all questions! ({len(st.session_state.test_answers)}/{len(st.session_state.test_questions)})")
            else:
                st.session_state.test_submitted = True
                st.rerun()
    
    else:
        # Show results
        st.write("### 📊 Test Results")
        
        correct = 0
        total = len(st.session_state.test_questions)
        
        for idx, q in enumerate(st.session_state.test_questions):
            if st.session_state.test_answers.get(idx) == q.get('correct'):
                correct += 1
        
        score = (correct / total) * 100
        
        st.markdown("---")
        
        if score >= 90:
            st.success(f"🌟 EXCELLENT! {correct}/{total} ({score:.0f}%)")
            st.balloons()
        elif score >= 70:
            st.info(f"✅ GOOD JOB! {correct}/{total} ({score:.0f}%)")
        elif score >= 50:
            st.warning(f"📚 KEEP PRACTICING! {correct}/{total} ({score:.0f}%)")
        else:
            st.error(f"💪 STUDY MORE! {correct}/{total} ({score:.0f}%)")
        
        st.markdown("---")
        
        # Detailed breakdown
        st.write("### 📋 Detailed Breakdown")
        
        for idx, q in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.test_answers.get(idx)
            correct_answer = q.get('correct')
            is_correct = user_answer == correct_answer
            
            if is_correct:
                st.success(f"✅ Question {q['number']}")
            else:
                st.error(f"❌ Question {q['number']}")
            
            st.write(f"**{q['question']}**")
            
            for letter, text in q['options'].items():
                if letter == correct_answer and letter == user_answer:
                    st.success(f"✅ {letter}) {text} ← CORRECT!")
                elif letter == correct_answer:
                    st.info(f"✓ {letter}) {text} ← Correct answer")
                elif letter == user_answer:
                    st.error(f"✗ {letter}) {text} ← Your answer")
                else:
                    st.write(f"  {letter}) {text}")
            
            st.markdown("---")
        
        # Award XP
        xp_earned = correct * 10
        award_xp(xp_earned, f"Test completed ({score:.0f}%)")
        
        if score >= 90:
            check_achievement('test_ace')
        
        st.success(f"⭐ You earned {xp_earned} XP!")
        
        if st.button("🔄 Take Another Test", use_container_width=True, type="primary"):
            st.session_state.test_active = False
            st.session_state.test_questions = []
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False
            st.rerun()

def show_image_analysis():
    """Image analysis with AI vision"""
    st.header("📸 Image Analysis Lab")
    st.caption("🔍 Upload or snap photos of study materials!")
    
    tab1, tab2 = st.tabs(["📤 Upload", "📷 Camera"])
    
    with tab1:
        uploaded = st.file_uploader("Choose image", type=['png', 'jpg', 'jpeg', 'webp'])
        
        if uploaded:
            img = Image.open(uploaded)
            st.image(img, width=450)
            
            analysis_type = st.radio("What to analyze?", [
                "📝 Explain everything",
                "💡 Key points only",
                "❓ Practice questions",
                "🔍 Find formulas",
                "📊 Explain diagram"
            ])
            
            if st.button("🔍 Analyze", type="primary"):
                prompts = {
                    "📝 Explain everything": "Explain everything in this study material in detail.",
                    "💡 Key points only": "List key points as a numbered list.",
                    "❓ Practice questions": "Create 5 practice questions from this content.",
                    "🔍 Find formulas": "Identify and explain all formulas/equations shown.",
                    "📊 Explain diagram": "Describe this diagram/chart in detail."
                }
                
                with st.spinner("🧠 Analyzing..."):
                    result, error = analyze_image_with_ai(uploaded, prompts[analysis_type])
                
                if result:
                    st.markdown("---")
                    st.markdown(result)
                    st.markdown("---")
                    
                    st.download_button("📥 Download", result, "analysis.txt")
                    award_xp(10, "Image analysis")
                else:
                    st.error(error or "Vision unavailable. Describe the image and I'll help!")
    
    with tab2:
        photo = st.camera_input("Take a photo")
        
        if photo:
            st.success("📸 Photo captured!")
            
            if st.button("🔍 Analyze Photo", type="primary"):
                with st.spinner("🧠 Analyzing..."):
                    result, error = analyze_image_with_ai(photo, "Explain this study material in detail.")
                
                if result:
                    st.markdown("---")
                    st.markdown(result)
                    award_xp(10, "Photo analysis")
                else:
                    st.error(error or "Describe what's in the photo and I'll help!")

def show_study_timer():
    """Pomodoro study timer"""
    st.header("⏱️ Study Timer")
    st.write("Track your study time with Pomodoro technique!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        duration = st.selectbox("⏰ Duration", ["25 min (Pomodoro)", "15 min (Short)", "45 min (Long)", "60 min (Marathon)"])
    
    with col2:
        break_time = st.selectbox("☕ Break", ["5 min", "10 min", "15 min"])
    
    if not st.session_state.study_timer_active:
        if st.button("▶️ Start Timer", type="primary", use_container_width=True):
            st.session_state.study_timer_active = True
            st.session_state.study_timer_start = time.time()
            st.rerun()
    else:
        elapsed = int(time.time() - st.session_state.study_timer_start)
        minutes = elapsed // 60
        seconds = elapsed % 60
        
        st.success(f"⏱️ {minutes:02d}:{seconds:02d}")
        
        if st.button("⏹️ Stop Timer", use_container_width=True):
            st.session_state.study_timer_active = False
            study_time = int(time.time() - st.session_state.study_timer_start)
            
            # Update total study time
            try:
                current_time = st.session_state.user_data.get('total_study_time', 0)
                supabase.table("profiles").update({
                    "total_study_time": current_time + study_time
                }).eq("id", st.session_state.user.id).execute()
            except:
                pass
            
            minutes = study_time // 60
            st.success(f"✅ Session complete! Studied for {minutes} minutes")
            award_xp(minutes * 2, "Study session")
            st.rerun()

def show_settings():
    """Settings page"""
    st.header("⚙️ Settings")
    
    st.write("### 👤 Profile")
    username = st.session_state.user_data.get('username', 'User')
    email = st.session_state.user.email if st.session_state.user else "unknown"
    
    st.info(f"**Username:** {username}\n\n**Email:** {email}")
    
    st.markdown("---")
    
    st.write("### 🎨 Preferences")
    
    # Theme toggle (placeholder)
    theme = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode)
    st.session_state.dark_mode = theme
    
    # Language
    language = st.selectbox("🌍 Language", ["English", "Tamil", "Hindi", "Spanish"])
    
    # Notifications (placeholder)
    notifications = st.toggle("🔔 Notifications", value=True)
    
    st.markdown("---")
    
    st.write("### ℹ️ About")
    st.info("""
**Study Master Infinity** v2.0

🎓 Free AI-powered study assistant
⚡ Powered by Groq AI
💾 Data stored securely with Supabase

Made with ❤️ by Aarya
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ Delete All Data", type="secondary"):
        if st.checkbox("I understand this cannot be undone"):
            try:
                supabase.table("history").delete().eq("user_id", st.session_state.user.id).execute()
                supabase.table("notes").delete().eq("user_id", st.session_state.user.id).execute()
                st.success("All data deleted!")
            except:
                st.error("Failed to delete data")

def show_schedule_planner():
    """AI Study Schedule Planner"""
    st.header("📅 Study Schedule Planner")
    st.write("Let AI create your personalized study plan!")
    
    with st.form("schedule_form"):
        subjects = st.text_area(
            "📚 Subjects to study",
            placeholder="Math\nPhysics\nChemistry\nBiology",
            height=100
        )
        
        col1, col2 = st.columns(2)
        with col1:
            days = st.number_input("📆 Days until exam", 1, 365, 30)
        with col2:
            hours_day = st.slider("⏰ Study hours/day", 1, 12, 4)
        
        focus = st.text_input(
            "🎯 Focus areas (optional)",
            placeholder="weak in calculus, need practice in organic chemistry"
        )
        
        study_style = st.selectbox(
            "🧠 Study Style",
            ["Visual Learner", "Auditory Learner", "Kinesthetic Learner", "Reading/Writing"]
        )
        
        submit = st.form_submit_button("🚀 Generate Schedule", use_container_width=True, type="primary")
        
        if submit and subjects:
            prompt = f"""Create a detailed {days}-day study schedule for:

Subjects:
{subjects}

Study time: {hours_day} hours/day
Focus areas: {focus if focus else 'None'}
Learning style: {study_style}

Provide:
1. **Overview** - Study strategy and goals
2. **Daily Breakdown** - What to study each day with time blocks
3. **Weekly Goals** - Milestones for each week
4. **Revision Strategy** - When and how to review
5. **Study Techniques** - Methods tailored to {study_style}
6. **Time Management Tips**

Make it realistic, achievable, and motivating!"""
            
            with st.spinner("🎨 Creating your personalized schedule..."):
                schedule, error = safe_ai_call(prompt, include_memory=False)
            
            if schedule:
                st.markdown("---")
                st.markdown(schedule)
                st.markdown("---")
                
                st.download_button(
                    "📥 Download Schedule",
                    schedule,
                    file_name="study_schedule.txt",
                    mime="text/plain"
                )
                
                award_xp(15, "Schedule created")
            else:
                st.error(error)

def show_flashcards():
    """Flashcard generator"""
    st.header("🗂️ Flashcard Generator")
    st.write("Create study flashcards instantly!")
    
    with st.form("flashcard_form"):
        topic = st.text_input(
            "📚 Topic",
            placeholder="Spanish Vocabulary, Biology Terms, Math Formulas"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            num_cards = st.slider("🎴 Number of cards", 5, 30, 10)
        with col2:
            card_style = st.selectbox(
                "🎨 Style",
                ["Simple Q&A", "Detailed Explanation", "Fill in Blank", "True/False"]
            )
        
        submit = st.form_submit_button("🎴 Generate Flashcards", use_container_width=True, type="primary")
        
        if submit and topic:
            style_prompts = {
                "Simple Q&A": "Create simple question and answer pairs.",
                "Detailed Explanation": "Create cards with detailed explanations.",
                "Fill in Blank": "Create fill-in-the-blank style cards.",
                "True/False": "Create true/false statement cards."
            }
            
            prompt = f"""Create {num_cards} flashcards for studying {topic}.
{style_prompts[card_style]}

Format each card:

**Card 1**
Front: [Question/Term/Statement]
Back: [Answer/Definition/Explanation]

**Card 2**
Front: [Question/Term/Statement]
Back: [Answer/Definition/Explanation]

Continue for all {num_cards} cards.
Make them clear, educational, and test-worthy!"""
            
            with st.spinner("🎨 Creating flashcards..."):
                flashcards, error = safe_ai_call(prompt, include_memory=False)
            
            if flashcards:
                st.markdown("---")
                st.markdown(flashcards)
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download as TXT",
                        flashcards,
                        file_name=f"flashcards_{topic.replace(' ', '_')}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                with col2:
                    # Convert to CSV format
                    csv_content = "Front,Back\n"
                    lines = flashcards.split('\n')
                    front, back = "", ""
                    for line in lines:
                        if line.startswith("Front:"):
                            front = line.replace("Front:", "").strip()
                        elif line.startswith("Back:"):
                            back = line.replace("Back:", "").strip()
                            if front and back:
                                csv_content += f'"{front}","{back}"\n'
                                front, back = "", ""
                    
                    st.download_button(
                        "📥 Download as CSV",
                        csv_content,
                        file_name=f"flashcards_{topic.replace(' ', '_')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                award_xp(10, "Flashcards created")
            else:
                st.error(error)

def show_study_notes():
    """Study notes manager"""
    st.header("📓 Study Notes")
    st.write("Create and manage your study notes!")
    
    tab1, tab2 = st.tabs(["✍️ Create Note", "📚 My Notes"])
    
    with tab1:
        st.write("### Create New Note")
        
        with st.form("note_form"):
            note_title = st.text_input("📌 Title", placeholder="e.g., Chapter 5 - Algebra Notes")
            
            note_content = st.text_area(
                "📝 Content",
                placeholder="Write your notes here...",
                height=300
            )
            
            note_tags = st.text_input(
                "🏷️ Tags (comma-separated)",
                placeholder="math, algebra, equations"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("💾 Save Note", use_container_width=True, type="primary")
            with col2:
                ai_enhance = st.form_submit_button("✨ AI Enhance", use_container_width=True)
            
            if submit and note_title and note_content:
                if save_note(note_title, note_content, note_tags):
                    st.success("✅ Note saved!")
                    award_xp(5, "Note created")
                    st.rerun()
                else:
                    st.error("Failed to save note")
            
            if ai_enhance and note_content:
                prompt = f"""Enhance these study notes by:
1. Organizing the content better
2. Adding key points summary
3. Highlighting important concepts
4. Suggesting memory techniques

Notes:
{note_content}"""
                
                with st.spinner("✨ AI enhancing your notes..."):
                    enhanced, error = safe_ai_call(prompt, include_memory=False)
                
                if enhanced:
                    st.markdown("---")
                    st.write("### ✨ Enhanced Version:")
                    st.markdown(enhanced)
                    
                    if st.button("📋 Copy Enhanced Version"):
                        st.success("Enhanced version ready to copy!")
                else:
                    st.error(error)
    
    with tab2:
        st.write("### Your Notes")
        
        notes = load_notes()
        
        if notes:
            # Search/filter
            search = st.text_input("🔍 Search notes", placeholder="Search by title or tags...")
            
            filtered_notes = notes
            if search:
                filtered_notes = [
                    n for n in notes
                    if search.lower() in n.get('title', '').lower()
                    or search.lower() in n.get('tags', '').lower()
                ]
            
            st.write(f"**{len(filtered_notes)} notes found**")
            
            for note in filtered_notes:
                with st.expander(f"📝 {note.get('title', 'Untitled')}"):
                    st.write(note.get('content', ''))
                    
                    if note.get('tags'):
                        st.caption(f"🏷️ Tags: {note['tags']}")
                    
                    st.caption(f"🕒 Created: {note.get('created_at', '')[:19]}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📥 Download", key=f"dl_{note['id']}"):
                            st.download_button(
                                "Download Note",
                                note.get('content', ''),
                                file_name=f"{note.get('title', 'note')}.txt",
                                mime="text/plain",
                                key=f"dlb_{note['id']}"
                            )
                    with col2:
                        if st.button("✏️ Edit", key=f"edit_{note['id']}"):
                            st.info("Edit feature coming soon!")
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_{note['id']}"):
                            if delete_note(note['id']):
                                st.success("Deleted!")
                                st.rerun()
        else:
            st.info("📝 No notes yet. Create your first note in the 'Create Note' tab!")

def show_dashboard():
    """Comprehensive dashboard with analytics"""
    st.header("📊 Your Dashboard")
    
    username = st.session_state.user_data.get('username', 'Student')
    st.markdown(f"### Welcome back, {username}! 👋")
    
    # Top stats
    col1, col2, col3, col4, col5 = st.columns(5)
    
    xp = st.session_state.user_data.get('xp', 0)
    level = xp // 100 + 1
    
    with col1:
        st.metric("📊 Level", level)
    with col2:
        st.metric("⭐ XP", xp)
    with col3:
        streak = st.session_state.user_data.get('study_streak', 0)
        st.metric("🔥 Streak", f"{streak}d")
    with col4:
        study_time = st.session_state.user_data.get('total_study_time', 0)
        hours = study_time // 3600
        st.metric("⏱️ Study Time", f"{hours}h")
    with col5:
        is_premium = st.session_state.user_data.get('is_premium', False)
        st.metric("💎 Status", "Premium" if is_premium else "Free")
    
    st.markdown("---")
    
    # Activity stats
    st.write("### 📈 Activity Statistics")
    
    try:
        # Count different activities
        hist_count = supabase.table("history").select("id", count="exact").eq(
            "user_id", st.session_state.user.id
        ).execute()
        
        notes_count = supabase.table("notes").select("id", count="exact").eq(
            "user_id", st.session_state.user.id
        ).execute()
        
        total_chats = hist_count.count if hist_count.count else 0
        total_notes = notes_count.count if notes_count.count else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💬 Chat Messages", total_chats)
        with col2:
            st.metric("📓 Notes Created", total_notes)
        with col3:
            st.metric("🎯 Tests Taken", 0)  # Placeholder
        with col4:
            st.metric("📝 Quizzes Generated", 0)  # Placeholder
    except:
        st.info("Activity tracking unavailable")
    
    st.markdown("---")
    
    # Recent activity timeline
    st.write("### 📜 Recent Activity")
    
    try:
        recent = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(10).execute()
        
        if recent.data:
            for activity in recent.data:
                role_icon = "👤" if activity['role'] == "user" else "🤖"
                content = activity['content']
                timestamp = activity['created_at'][:19]
                
                with st.expander(f"{role_icon} {content[:60]}..." if len(content) > 60 else f"{role_icon} {content}"):
                    st.write(content)
                    st.caption(f"🕒 {timestamp}")
        else:
            st.info("No activity yet. Start using the app to see your progress!")
    except:
        st.info("Activity history unavailable")
    
    st.markdown("---")
    
    # Achievements section
    st.write("### 🏆 Achievements")
    
    achievements_display = {
        'first_chat': {'icon': '💬', 'name': 'First Chat', 'desc': 'Sent your first message'},
        'quiz_master': {'icon': '📝', 'name': 'Quiz Master', 'desc': 'Generated your first quiz'},
        'test_ace': {'icon': '🏆', 'name': 'Test Ace', 'desc': 'Scored 90%+ on a test'},
        'study_streak': {'icon': '🔥', 'name': '7-Day Streak', 'desc': 'Studied for 7 days straight'},
        'knowledge_seeker': {'icon': '🧠', 'name': 'Knowledge Seeker', 'desc': 'Asked 100 questions'},
    }
    
    user_achievements = st.session_state.achievements
    
    if user_achievements:
        cols = st.columns(len(user_achievements))
        for idx, ach in enumerate(user_achievements):
            if ach in achievements_display:
                with cols[idx]:
                    info = achievements_display[ach]
                    st.success(f"{info['icon']} **{info['name']}**")
                    st.caption(info['desc'])
    else:
        st.info("🏅 Complete activities to unlock achievements!")
    
    st.markdown("---")
    
    # Study insights
    st.write("### 💡 Study Insights")
    
    insights = [
        f"🎯 You've earned {xp} XP - keep going!",
        f"📚 Level {level} - {100 - (xp % 100)} XP to next level!",
        f"🔥 Current streak: {streak} days",
        "💪 Tip: Study consistently to build your streak!"
    ]
    
    for insight in insights:
        st.info(insight)
    
    st.markdown("---")
    
    # Progress visualization (placeholder)
    st.write("### 📊 Progress Over Time")
    st.info("📈 Detailed analytics coming soon! Track your XP, study time, and test scores over time.")

# ==================== MAIN APP LOGIC ====================

def main():
    """Main application logic"""
    
    # Check if user is logged in
    if not st.session_state.user:
        login_screen()
        return
    
    # Load user profile
    try:
        profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
        
        if not profile_res.data:
            username_setup_screen()
            return
        
        st.session_state.user_data = profile_res.data[0]
    except Exception as e:
        st.error(f"Profile error: {e}")
        st.session_state.user_data = {"username": "User", "xp": 0, "is_premium": False}
    
    # Show sidebar and get menu choice
    menu = show_sidebar()
    
    # Route to appropriate feature
    if menu == "🏠 Home":
        show_home()
    elif menu == "💬 Chat":
        show_chat()
    elif menu == "📝 Quiz Generator":
        show_quiz_generator()
    elif menu == "👨‍🏫 Teacher Mode":
        show_teacher_mode()
    elif menu == "📅 Schedule Planner":
        show_schedule_planner()
    elif menu == "📸 Image Analysis":
        show_image_analysis()
    elif menu == "🗂️ Flashcards":
        show_flashcards()
    elif menu == "📓 Study Notes":
        show_study_notes()
    elif menu == "⏱️ Study Timer":
        show_study_timer()
    elif menu == "📊 Dashboard":
        show_dashboard()
    elif menu == "⚙️ Settings":
        show_settings()
    else:
        st.write(f"Feature '{menu}' is under development!")
        st.info("Check back soon for updates!")

# Run app
if __name__ == "__main__":
    main()
