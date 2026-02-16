import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, time
import PIL.Image
import os
import json

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🎓")

# Custom CSS for beautiful UI + Proper Stop Button
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
if "pending_message" not in st.session_state:
    st.session_state.pending_message = None

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
                st.write("• 250 uses/day")
                st.write("• Priority support")
                st.write("• Early features")
                code = st.text_input("Code", type="password", key="prem")
                if st.button("Activate", key="activate_premium", use_container_width=True):
                    if code == "STUDY777":
                        st.session_state.is_premium = True
                        st.success("🎉 Premium!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Invalid")
        else:
            st.success("⭐ Premium Active")
        
        st.markdown("---")
        
        # Usage
        usage = get_daily_usage()
        limit = 250 if st.session_state.is_premium else 50
        
        if usage >= limit:
            st.error(f"🚫 {usage}/{limit}")
        else:
            st.metric("Daily Usage", f"{usage}/{limit}")
        
        st.progress(min(usage/limit, 1.0))
        st.caption("⏰ Resets in 24h")
        
        st.markdown("---")
        
        # Menu
        menu = st.radio("📚 Navigation", [
            "💬 Chat",
            "📝 Quiz",
            "📁 Image",
            "🎯 Tutor",
            "📅 Planner"
        ], label_visibility="collapsed")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.chat_messages = []
            st.rerun()
    
    # Check limit
    if usage >= limit and menu != "📅 Planner":
        st.error("⚠️ Daily limit reached!")
        st.info("💎 Upgrade to Premium for 250/day")
        st.stop()
    
    # CHAT - COMPLETELY FIXED
    if menu == "💬 Chat":
        st.title("💬 AI Study Assistant")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("Ask me anything about your studies!")
        with col2:
            if st.button("📜 Load History", key="load_hist"):
                loaded = load_chat_history()
                if loaded:
                    st.session_state.chat_messages = loaded
                    st.success(f"✅ Loaded {len(loaded)//2} chats")
                    st.rerun()
        with col3:
            if st.button("🗑️ Clear All", key="clear_hist"):
                if clear_chat_history():
                    st.success("✅ Cleared")
                    st.rerun()
        
        st.markdown("---")
        
        # Display ALL messages
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Display assistant response if currently generating
        if st.session_state.is_generating and st.session_state.pending_message:
            # Show user message first
            with st.chat_message("user"):
                st.markdown(st.session_state.pending_message)
            
            # Generate assistant response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = stream_response(st.session_state.pending_message, message_placeholder)
                
                st.session_state.chat_messages.append({"role": "user", "content": st.session_state.pending_message})
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                
                if "[⏹️" not in full_response:
                    save_chat_message(st.session_state.pending_message, full_response)
                
                st.session_state.is_generating = False
                st.session_state.pending_message = None
                st.rerun()
        
        # Chat input - ONLY STOP BUTTON APPEARS DURING GENERATION
        if st.session_state.is_generating:
            # Show stop button message
            st.info("⏹️ Generating response... (refresh to cancel)")
        else:
            # Normal chat input
            prompt = st.chat_input("Type your question...", key="chat_input")
            
            if prompt:
                st.session_state.pending_message = prompt
                st.session_state.is_generating = True
                st.session_state.stop_generation = False
                st.rerun()
    
    # QUIZ - BUTTON REPLACEMENT
    elif menu == "📝 Quiz":
        st.title("📝 Quiz Generator")
        
        topic = st.text_input("📚 Topic:", key="quiz_topic", placeholder="e.g., World War 2, Photosynthesis")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("🎯 Difficulty:", ["Easy", "Medium", "Hard"], key="quiz_diff")
        with col2:
            num_questions = st.slider("❓ Questions:", 3, 10, 5, key="quiz_num")
        
        # BUTTON REPLACEMENT - Only one button visible at a time
        if not st.session_state.is_generating:
            # Show GENERATE button
            if st.button("🎯 Generate Quiz", use_container_width=True, key="gen_quiz", type="primary"):
                if not topic:
                    st.error("❌ Enter a topic first!")
                else:
                    st.session_state.is_generating = True
                    st.session_state.quiz_generated = False
                    st.session_state.current_response = ""
                    st.rerun()
        else:
            # Show STOP button (Generate is completely hidden)
            if st.button("⏹️ Stop Generating", use_container_width=True, key="stop_quiz_btn", type="secondary"):
                st.session_state.stop_generation = True
        
        # Generate quiz
        if st.session_state.is_generating and topic and not st.session_state.quiz_generated:
            st.markdown("---")
            st.markdown("### 📝 Your Quiz")
            response_placeholder = st.empty()
            
            prompt = f"""Create a {num_questions}-question multiple choice quiz about {topic} at {difficulty} difficulty.

Format each question like this:

**Question 1:** [question text]
A) [option]
B) [option]
C) [option]
D) [option]

[repeat for all questions]

**Answer Key:**
1. [correct letter]
2. [correct letter]
etc."""
            
            full_response = stream_response(prompt, response_placeholder)
            
            st.session_state.quiz_generated = True
            st.session_state.current_response = full_response
            
            st.markdown("---")
            
            if "[⏹️" not in full_response:
                st.download_button(
                    "📥 Download Quiz",
                    data=full_response,
                    file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                    mime="text/plain",
                    key="dl_quiz"
                )
                
                if supabase:
                    supabase.table("history").insert({
                        "user_id": st.session_state.user.id,
                        "question": f"Quiz: {topic} ({difficulty})",
                        "answer": full_response
                    }).execute()
            
            st.session_state.is_generating = False
            st.rerun()
        
        # Show generated quiz
        elif st.session_state.quiz_generated and st.session_state.current_response:
            st.markdown("---")
            st.markdown("### 📝 Your Quiz")
            st.markdown(st.session_state.current_response)
            st.markdown("---")
            
            st.download_button(
                "📥 Download Quiz",
                data=st.session_state.current_response,
                file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                mime="text/plain",
                key="dl_quiz_saved"
            )
    
    # IMAGE - BUTTON REPLACEMENT
    elif menu == "📁 Image":
        st.title("📁 Image Analysis")
        
        file = st.file_uploader("📤 Upload study material:", type=['jpg', 'png', 'jpeg'], key="img_up")
        
        if file:
            img = PIL.Image.open(file)
            st.image(img, use_container_width=True, caption="Uploaded Image")
            
            # BUTTON REPLACEMENT
            if not st.session_state.is_generating:
                if st.button("🔍 Analyze Image", use_container_width=True, key="analyze_img", type="primary"):
                    st.session_state.is_generating = True
                    st.rerun()
            else:
                if st.button("⏹️ Stop Analysis", use_container_width=True, key="stop_img_btn", type="secondary"):
                    st.session_state.stop_generation = True
            
            if st.session_state.is_generating:
                st.markdown("---")
                st.markdown("### 📊 Analysis Results")
                response_placeholder = st.empty()
                
                prompt = """Analyze this study material in detail:

1. **Summary** - What is this about?
2. **Key Concepts** - Main ideas and topics
3. **Important Details** - Facts, formulas, dates, definitions
4. **Study Tips** - How to remember and understand this
5. **Practice Questions** - 3 questions to test understanding"""
                
                full_response = stream_response(prompt, response_placeholder, is_image=True, image=img)
                
                st.markdown("---")
                
                if "[⏹️" not in full_response and supabase:
                    supabase.table("history").insert({
                        "user_id": st.session_state.user.id,
                        "question": "Image Analysis",
                        "answer": full_response
                    }).execute()
                
                st.session_state.is_generating = False
                st.rerun()
    
    # TUTOR - BUTTON REPLACEMENT
    elif menu == "🎯 Tutor":
        st.title("🎯 Socratic Tutor")
        st.info("💡 Learn through guided questions instead of direct answers!")
        
        problem = st.text_area("📝 Describe your problem or question:", height=150, key="tutor_prob", 
                               placeholder="e.g., I don't understand how photosynthesis works...")
        
        # BUTTON REPLACEMENT
        if not st.session_state.is_generating:
            if st.button("🚀 Start Tutoring Session", use_container_width=True, key="start_tutor", type="primary"):
                if not problem:
                    st.error("❌ Please describe your problem first!")
                else:
                    st.session_state.is_generating = True
                    st.rerun()
        else:
            if st.button("⏹️ Stop Session", use_container_width=True, key="stop_tutor_btn", type="secondary"):
                st.session_state.stop_generation = True
        
        if st.session_state.is_generating and problem:
            st.markdown("---")
            st.markdown("### 🧠 Guiding Questions")
            response_placeholder = st.empty()
            
            prompt = f"""Act as a Socratic tutor for this student problem:

"{problem}"

Do NOT give the direct answer. Instead:
1. Ask 3-4 thought-provoking guiding questions
2. Help them discover the answer through their own thinking
3. Encourage critical thinking and deeper understanding
4. Be supportive and encouraging

Start with: "Let me help you think through this step by step..."
"""
            
            full_response = stream_response(prompt, response_placeholder)
            
            st.markdown("---")
            
            if "[⏹️" not in full_response and supabase:
                supabase.table("history").insert({
                    "user_id": st.session_state.user.id,
                    "question": f"Socratic: {problem[:100]}",
                    "answer": full_response
                }).execute()
            
            st.session_state.is_generating = False
            st.rerun()
    
    # PLANNER
    elif menu == "📅 Planner":
        st.title("📅 Study Schedule Planner")
        
        tab1, tab2, tab3 = st.tabs(["➕ Create Schedule", "📋 My Schedules", "🤖 AI Generator"])
        
        with tab1:
            st.markdown("### ✏️ Manual Schedule Creation")
            
            name = st.text_input("📌 Schedule Name:", placeholder="e.g., Finals Week", key="sched_name")
            
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("📅 Start Date:", key="start")
            with col2:
                end = st.date_input("📅 End Date:", key="end")
            
            st.markdown("### 📚 Study Blocks")
            
            blocks = st.number_input("Number of blocks:", 1, 10, 3, key="blocks")
            
            study_blocks = []
            for i in range(blocks):
                with st.expander(f"📖 Block {i+1}", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        subj = st.text_input("Subject:", key=f"subj_{i}", placeholder="Math")
                    with col2:
                        tm = st.time_input("Start Time:", value=time(9, 0), key=f"tm_{i}")
                    with col3:
                        dur = st.selectbox("Duration:", ["30 min", "1 hour", "1.5 hours", "2 hours"], key=f"dur_{i}")
                    
                    topic = st.text_input("Topic/Task:", key=f"top_{i}", placeholder="Chapter 5 - Calculus")
                    
                    if subj and topic:
                        study_blocks.append({
                            "subject": subj,
                            "start_time": tm.strftime("%H:%M"),
                            "duration": dur,
                            "topic": topic
                        })
            
            if st.button("💾 Save Schedule", use_container_width=True, key="save_sched", type="primary"):
                if not name:
                    st.error("❌ Enter a schedule name!")
                elif not study_blocks:
                    st.error("❌ Add at least one study block!")
                else:
                    data = {
                        "name": name,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "blocks": study_blocks
                    }
                    if save_schedule(data):
                        st.success("✅ Schedule saved successfully!")
                        st.balloons()
        
        with tab2:
            st.markdown("### 📋 Your Saved Schedules")
            
            schedules = load_schedules()
            
            if not schedules:
                st.info("📅 No schedules yet. Create one in the 'Create Schedule' tab!")
            else:
                for sched in schedules:
                    data = json.loads(sched["schedule_data"])
                    
                    with st.expander(f"📅 {data['name']}", expanded=False):
                        st.write(f"**📆 Period:** {data['start_date']} to {data['end_date']}")
                        
                        st.markdown("**📚 Study Blocks:**")
                        for i, b in enumerate(data['blocks'], 1):
                            st.write(f"**{i}. {b['subject']}** - ⏰ {b['start_time']} ({b['duration']})")
                            st.write(f"   📖 {b['topic']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            txt = f"{data['name']}\n{data['start_date']} to {data['end_date']}\n\n"
                            for i, b in enumerate(data['blocks'], 1):
                                txt += f"{i}. {b['subject']} - {b['start_time']} ({b['duration']})\n   {b['topic']}\n\n"
                            
                            st.download_button("📥 Download", data=txt, file_name=f"{data['name']}.txt", key=f"dl_{sched['id']}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_{sched['id']}"):
                                if delete_schedule(sched['id']):
                                    st.success("✅ Deleted!")
                                    st.rerun()
        
        with tab3:
            st.markdown("### 🤖 AI-Powered Schedule Generator")
            st.info("✨ Let AI create an optimized study plan tailored to your needs!")
            
            exam = st.date_input("📅 Exam/Deadline Date:", key="ai_exam")
            subjects = st.text_area("📚 Subjects (one per line):", 
                                    placeholder="Math\nPhysics\nChemistry\nBiology", 
                                    key="ai_subj",
                                    height=120)
            
            col1, col2 = st.columns(2)
            with col1:
                hrs = st.slider("⏰ Study hours per day:", 1, 12, 4, key="ai_hrs")
            with col2:
                diff = st.selectbox("🎯 Overall difficulty:", ["Easy", "Medium", "Hard"], key="ai_diff")
            
            prefs = st.text_area("💭 Special preferences (optional):", 
                                 placeholder="e.g., I'm a morning person, need breaks every hour, weak in Math",
                                 key="ai_prefs",
                                 height=80)
            
            # BUTTON REPLACEMENT
            if not st.session_state.is_generating:
                if st.button("🎯 Generate AI Schedule", use_container_width=True, key="gen_ai", type="primary"):
                    if not subjects:
                        st.error("❌ Enter at least one subject!")
                    else:
                        st.session_state.is_generating = True
                        st.rerun()
            else:
                if st.button("⏹️ Stop Generating", use_container_width=True, key="stop_ai_btn", type="secondary"):
                    st.session_state.stop_generation = True
            
            if st.session_state.is_generating and subjects:
                st.markdown("---")
                st.markdown("### 📋 Your AI-Generated Schedule")
                response_placeholder = st.empty()
                
                days = (exam - datetime.now().date()).days
                
                prompt = f"""Create a detailed and realistic study schedule with these parameters:

- **Days until exam:** {days} days
- **Subjects:** {subjects}
- **Daily study time:** {hrs} hours
- **Difficulty level:** {diff}
- **Student preferences:** {prefs if prefs else 'None specified'}

Please provide:
1. **Overview** - Study strategy and approach summary
2. **Daily Breakdown** - What to study each day with specific time blocks
3. **Study Tips** - Effective techniques for these subjects
4. **Revision Plan** - When and how to review each subject
5. **Break Schedule** - Recommended breaks and rest periods

Make it realistic, achievable, and well-balanced!"""
                
                full_response = stream_response(prompt, response_placeholder)
                
                st.markdown("---")
                
                if "[⏹️" not in full_response:
                    st.download_button(
                        "📥 Download AI Schedule",
                        data=full_response,
                        file_name="ai_study_schedule.txt",
                        mime="text/plain",
                        key="dl_ai"
                    )
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"AI Schedule: {subjects.split()[0]}... ({days} days)",
                            "answer": full_response
                        }).execute()
                
                st.session_state.is_generating = False
                st.rerun()

else:
    login_screen()

