import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, time
import PIL.Image
import os
import json

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

# Custom CSS for beautiful UI + Circular Stop Button
st.markdown("""
<style>
    /* Main color scheme */
    :root {
        --primary-color: #6366f1;
        --secondary-color: #8b5cf6;
        --accent-color: #ec4899;
    }
    
    /* Improve chat messages */
    .stChatMessage {
        background-color: rgba(99, 102, 241, 0.05);
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
    }
    
    /* Beautiful buttons */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(99, 102, 241, 0.3);
    }
    
    /* CIRCULAR STOP BUTTON */
    .stop-button button {
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 0 !important;
        font-size: 20px !important;
        background-color: #ef4444 !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3) !important;
    }
    
    .stop-button button:hover {
        background-color: #dc2626 !important;
        transform: scale(1.1) !important;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.5) !important;
    }
    
    /* Card-like containers */
    .element-container {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
    }
    
    /* Headers */
    h1, h2, h3 {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    
    /* Input fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 10px;
        border: 2px solid rgba(99, 102, 241, 0.3);
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #6366f1;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: rgba(99, 102, 241, 0.1);
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 2px dashed rgba(99, 102, 241, 0.4);
        border-radius: 15px;
        padding: 20px;
        background: rgba(99, 102, 241, 0.05);
    }
    
    /* Chat input container alignment */
    .chat-input-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
</style>
""", unsafe_allow_html=True)

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

# --- 3. GEMINI INIT ---
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
        
        st.info("🔍 Scanning for AI models...")
        
        try:
            all_models = genai.list_models()
            valid_models = [
                m for m in all_models 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            if not valid_models:
                st.error("No compatible models!")
                return None
            
            st.success(f"✅ Found {len(valid_models)} models")
            
            for model_info in valid_models:
                model_name = model_info.name
                
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content("test")
                    if response.text:
                        st.success(f"🎉 Connected: {model_name}")
                        return model
                except:
                    pass
                
                try:
                    short_name = model_name.replace("models/", "")
                    model = genai.GenerativeModel(short_name)
                    response = model.generate_content("test")
                    if response.text:
                        st.success(f"🎉 Connected: {short_name}")
                        return model
                except:
                    pass
            
            st.error("All models failed!")
            return None
            
        except Exception as e:
            st.error(f"Failed: {e}")
            return None
            
    except Exception as e:
        st.error(f"Fatal: {e}")
        return None

supabase = initialize_supabase()
model = initialize_gemini()

# --- 4. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "stop_generation" not in st.session_state:
    st.session_state.stop_generation = False
if "current_response" not in st.session_state:
    st.session_state.current_response = ""
if "quiz_generated" not in st.session_state:
    st.session_state.quiz_generated = False

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

# --- 6. CHAT FUNCTIONS ---
def load_chat_history():
    if not supabase or not st.session_state.user:
        return []
    try:
        res = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(50).execute()
        
        if res.data:
            messages = []
            for item in reversed(res.data):
                messages.append({"role": "user", "content": item["question"]})
                messages.append({"role": "assistant", "content": item["answer"]})
            return messages
        return []
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
        st.session_state.chat_messages = []
        return True
    except:
        return False

# --- 7. SCHEDULE FUNCTIONS ---
def save_schedule(schedule_data):
    if not supabase or not st.session_state.user:
        return False
    try:
        supabase.table("schedules").insert({
            "user_id": st.session_state.user.id,
            "schedule_name": schedule_data["name"],
            "schedule_data": json.dumps(schedule_data),
            "created_at": datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

def load_schedules():
    if not supabase or not st.session_state.user:
        return []
    try:
        res = supabase.table("schedules").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).execute()
        return res.data if res.data else []
    except:
        return []

def delete_schedule(schedule_id):
    if not supabase:
        return False
    try:
        supabase.table("schedules").delete().eq("id", schedule_id).execute()
        return True
    except:
        return False

# --- 8. STREAMING FUNCTION ---
def stream_response(prompt, placeholder, is_image=False, image=None):
    try:
        full_response = ""
        
        if is_image and image:
            response = model.generate_content([prompt, image], stream=True)
        else:
            response = model.generate_content(prompt, stream=True)
        
        for chunk in response:
            if st.session_state.stop_generation:
                full_response += "\n\n[⏹️ Stopped by user]"
                break
            
            if hasattr(chunk, 'text'):
                full_response += chunk.text
                placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
        return full_response
        
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        placeholder.error(error_msg)
        return error_msg

# --- 9. LOGIN SCREEN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center;'>🎓 Study Master Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #6366f1;'>Your AI-Powered Study Companion</p>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.info("💬 **AI Chat**\nInstant answers")
        with col_b:
            st.info("📝 **Quizzes**\nCustom tests")
        with col_c:
            st.info("📅 **Planner**\nSmart schedules")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not supabase:
            st.error("⚠️ Connection failed")
            return
        
        tab1, tab2 = st.tabs(["🔑 Login", "✨ Sign Up"])
        
        with tab1:
            email = st.text_input("📧 Email", key="l_email")
            password = st.text_input("🔒 Password", type="password", key="l_pass")
            
            if st.button("🚀 Log In", use_container_width=True, type="primary"):
                if email and password:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        st.success("✅ Welcome back!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
                else:
                    st.error("❌ Fill all fields")
        
        with tab2:
            st.info("🎁 Get 50 free AI interactions daily!")
            
            new_email = st.text_input("📧 Email", key="s_email")
            new_pass = st.text_input("🔒 Password (6+ chars)", type="password", key="s_pass")
            confirm_pass = st.text_input("🔒 Confirm", type="password", key="s_confirm")
            agree = st.checkbox("✅ I agree to Terms", key="agree")
            
            if st.button("🎉 Create Account", use_container_width=True, type="primary"):
                if not new_email or not new_pass:
                    st.error("❌ Fill all fields")
                elif len(new_pass) < 6:
                    st.error("❌ Password too short")
                elif new_pass != confirm_pass:
                    st.error("❌ Passwords don't match")
                elif not agree:
                    st.error("❌ Accept Terms")
                else:
                    try:
                        res = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                        if res.user:
                            st.session_state.user = res.user
                            st.success("🎉 Account created!")
                            st.balloons()
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.success("✅ Check your email!")
                    except Exception as e:
                        if "already registered" in str(e).lower():
                            st.error("❌ Email exists")
                        else:
                            st.error(f"❌ {e}")

# --- 10. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("⚠️ AI unavailable")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 💎 Study Master Pro")
        st.markdown(f"**👋 {st.session_state.user.email.split('@')[0]}**")
        
        st.markdown("---")
        
        # Premium
        if not st.session_state.is_premium:
            with st.expander("⭐ Go Premium"):
                st.write("**Benefits:**")
                st.write("• 250
