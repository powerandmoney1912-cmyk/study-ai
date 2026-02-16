import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, time
import PIL.Image
import os
import json

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

# --- 3. BULLETPROOF GEMINI INIT ---
@st.cache_resource
def initialize_gemini():
    """Auto-detects working model"""
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
        
        st.info("🔍 Scanning for available AI models...")
        
        try:
            all_models = genai.list_models()
            valid_models = [
                m for m in all_models 
                if 'generateContent' in m.supported_generation_methods
            ]
            
            if not valid_models:
                st.error("No compatible models found!")
                return None
            
            model_names = [m.name for m in valid_models]
            st.success(f"✅ Found {len(model_names)} models")
            
            for model_info in valid_models:
                model_name = model_info.name
                
                try:
                    st.info(f"Testing: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content("Say ready")
                    if response.text:
                        st.success(f"🎉 CONNECTED: {model_name}")
                        return model
                except:
                    pass
                
                try:
                    short_name = model_name.replace("models/", "")
                    model = genai.GenerativeModel(short_name)
                    response = model.generate_content("Say ready")
                    if response.text:
                        st.success(f"🎉 CONNECTED: {short_name}")
                        return model
                except:
                    pass
            
            st.error("All models failed!")
            return None
            
        except Exception as e:
            st.error(f"Model list failed: {e}")
            return None
            
    except Exception as e:
        st.error(f"Fatal error: {e}")
        return None

# Initialize
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

# --- 6. CHAT HISTORY FUNCTIONS ---
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

# --- 8. STREAMING WITH STOP CAPABILITY ---
def stream_response(prompt, placeholder, is_image=False, image=None):
    """Stream AI response with ability to stop"""
    try:
        full_response = ""
        
        if is_image and image:
            response = model.generate_content([prompt, image], stream=True)
        else:
            response = model.generate_content(prompt, stream=True)
        
        for chunk in response:
            if st.session_state.stop_generation:
                full_response += "\n\n[⏹️ Generation stopped]"
                break
            
            if hasattr(chunk, 'text'):
                full_response += chunk.text
                placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
        return full_response
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        placeholder.error(error_msg)
        return error_msg

# --- 9. LOGIN SCREEN ---
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
        st.error("Connection failed.")
        return
    
    tab1, tab2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    
    with tab1:
        st.write("### Welcome Back!")
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("🚀 Log In", use_container_width=True, type="primary"):
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.success("✅ Logged in!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")
            else:
                st.error("Enter email and password")
    
    with tab2:
        st.write("### Create Account")
        st.info("🎁 Get 50 free AI interactions daily!")
        
        new_email = st.text_input("Email", key="s_email", placeholder="student@example.com")
        new_pass = st.text_input("Password (6+ chars)", type="password", key="s_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="s_confirm")
        agree = st.checkbox("I agree to Terms of Service", key="agree")
        
        if st.button("🎉 Create Account", use_container_width=True, type="primary"):
            if not new_email or not new_pass:
                st.error("❌ Fill all fields")
            elif len(new_pass) < 6:
                st.error("❌ Password too short")
            elif new_pass != confirm_pass:
                st.error("❌ Passwords don't match")
            elif not agree:
                st.error("❌ Agree to Terms")
            else:
                try:
                    res = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                    if res.user:
                        st.session_state.user = res.user
                        st.success("🎉 Account created! You're logged in!")
                        st.balloons()
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.success("✅ Account created! Check email to verify.")
                except Exception as e:
                    if "already registered" in str(e).lower():
                        st.error("❌ Email already registered")
                    else:
                        st.error(f"❌ Signup failed: {e}")

# --- 10. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("⚠️ AI unavailable")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master Pro")
    st.sidebar.write(f"👋 **{st.session_state.user.email.split('@')[0]}**")
    
    # Premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("⭐ Premium"):
            st.write("✅ 250 uses/day\n✅ Priority support")
            code = st.text_input("Code", type="password", key="prem")
            if st.button("Activate", key="activate_premium"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("🎉 Premium!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Invalid")
    else:
        st.sidebar.success("⭐ Premium")
    
    # Usage
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    
    if usage >= limit:
        st.sidebar.error(f"🚫 {usage}/{limit}")
    else:
        st.sidebar.metric("Usage", f"{usage}/{limit}")
    
    st.sidebar.progress(min(usage/limit, 1.0))
    st.sidebar.caption("⏰ Resets every 24h")
    
    # Menu
    menu = st.sidebar.radio("📚 Menu", [
        "💬 Chat", 
        "📝 Quiz", 
        "📁 Image", 
        "🎯 Tutor",
        "📅 Planner"
    ])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.chat_messages = []
        st.rerun()
    
    # Check limit
    if usage >= limit and menu != "📅 Planner":
        st.error(f"⚠️ Limit reached ({usage}/{limit})")
        st.info("💎 Upgrade to Premium for 250/day!")
        st.stop()
    
    # CHAT
    if menu == "💬 Chat":
        st.subheader("💬 AI Study Assistant")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("Ask me anything")
        with col2:
            if st.button("📜 Load", key="load_hist"):
                loaded = load_chat_history()
                if loaded:
                    st.session_state.chat_messages = loaded
                    st.success(f"Loaded {len(loaded)//2} chats!")
                    st.rerun()
        with col3:
            if st.button("🗑️ Clear", key="clear_hist"):
                if clear_chat_history():
                    st.success("Cleared!")
                    st.rerun()
        
        st.markdown("---")
        
        # Display messages
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask...", key="chat_input", disabled=st.session_state.is_generating):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                
                st.session_state.is_generating = True
                st.session_state.stop_generation = False
                
                full_response = stream_response(prompt, message_placeholder)
                
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                
                if "[⏹️" not in full_response:
                    save_chat_message(prompt, full_response)
                
                st.session_state.is_generating = False
                st.rerun()
    
    # QUIZ
    elif menu == "📝 Quiz":
        st.subheader("📝 Quiz Generator")
        
        topic = st.text_input("Topic:", key="quiz_topic", placeholder="e.g., Biology")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], key="quiz_diff")
        with col2:
            num_questions = st.slider("Questions:", 3, 10, 5, key="quiz_num")
        
        # BUTTON REPLACEMENT LOGIC
        button_container = st.empty()
        
        if not st.session_state.is_generating:
            if button_container.button("🎯 Generate Quiz", use_container_width=True, key="gen_quiz", type="primary"):
                if not topic:
                    st.error("Enter a topic!")
                else:
                    st.session_state.is_generating = True
                    st.rerun()
        else:
            if button_container.button("⏹️ Stop Generating", use_container_width=True, key="stop_quiz", type="secondary"):
                st.session_state.stop_generation = True
        
        # Generate if triggered
        if st.session_state.is_generating and topic:
            st.markdown("---")
            response_placeholder = st.empty()
            
            prompt = f"""Create {num_questions} multiple choice questions about {topic} at {difficulty} level.

Format:
**Question 1:** [question]
A) B) C) D)

**Answer Key:**
1. [letter]"""
            
            full_response = stream_response(prompt, response_placeholder)
            
            st.markdown("---")
            
            if "[⏹️" not in full_response:
                st.download_button(
                    "📥 Download",
                    data=full_response,
                    file_name=f"quiz_{topic}.txt",
                    key="dl_quiz"
                )
                
                if supabase:
                    supabase.table("history").insert({
                        "user_id": st.session_state.user.id,
                        "question": f"Quiz: {topic}",
                        "answer": full_response
                    }).execute()
            
            st.session_state.is_generating = False
            st.rerun()
    
    # IMAGE
    elif menu == "📁 Image":
        st.subheader("📁 Image Analysis")
        
        file = st.file_uploader("Upload:", type=['jpg', 'png', 'jpeg'], key="img_up")
        
        if file:
            img = PIL.Image.open(file)
            st.image(img, use_container_width=True)
            
            # BUTTON REPLACEMENT
            button_container = st.empty()
            
            if not st.session_state.is_generating:
                if button_container.button("🔍 Analyze", use_container_width=True, key="analyze_img", type="primary"):
                    st.session_state.is_generating = True
                    st.rerun()
            else:
                if button_container.button("⏹️ Stop", use_container_width=True, key="stop_img", type="secondary"):
                    st.session_state.stop_generation = True
            
            if st.session_state.is_generating:
                st.markdown("---")
                response_placeholder = st.empty()
                
                prompt = """Analyze:
1. Summary
2. Key Concepts
3. Important Details
4. Study Tips
5. Practice Questions"""
                
                full_response = stream_response(prompt, response_placeholder, is_image=True, image=img)
                
                if "[⏹️" not in full_response and supabase:
                    supabase.table("history").insert({
                        "user_id": st.session_state.user.id,
                        "question": "Image Analysis",
                        "answer": full_response
                    }).execute()
                
                st.session_state.is_generating = False
                st.rerun()
    
    # TUTOR
    elif menu == "🎯 Tutor":
        st.subheader("🎯 Socratic Tutor")
        st.info("💡 Learn through guided questions")
        
        problem = st.text_area("Your problem:", height=150, key="tutor_prob")
        
        # BUTTON REPLACEMENT
        button_container = st.empty()
        
        if not st.session_state.is_generating:
            if button_container.button("🚀 Start", use_container_width=True, key="start_tutor", type="primary"):
                if not problem:
                    st.error("Describe your problem!")
                else:
                    st.session_state.is_generating = True
                    st.rerun()
        else:
            if button_container.button("⏹️ Stop", use_container_width=True, key="stop_tutor", type="secondary"):
                st.session_state.stop_generation = True
        
        if st.session_state.is_generating and problem:
            st.markdown("---")
            response_placeholder = st.empty()
            
            prompt = f"""Socratic tutor for: "{problem}"
Ask 3-4 guiding questions.
Don't give answers."""
            
            full_response = stream_response(prompt, response_placeholder)
            
            if "[⏹️" not in full_response and supabase:
                supabase.table("history").insert({
                    "user_id": st.session_state.user.id,
                    "question": f"Socratic: {problem}",
                    "answer": full_response
                }).execute()
            
            st.session_state.is_generating = False
            st.rerun()
    
    # PLANNER
    elif menu == "📅 Planner":
        st.subheader("📅 Study Planner")
        
        tab1, tab2, tab3 = st.tabs(["➕ Create", "📋 Saved", "🤖 AI"])
        
        with tab1:
            name = st.text_input("Name:", placeholder="Finals", key="sched_name")
            
            col1, col2 = st.columns(2)
            with col1:
                start = st.date_input("Start:", key="start")
            with col2:
                end = st.date_input("End:", key="end")
            
            blocks = st.number_input("Blocks:", 1, 10, 3, key="blocks")
            
            study_blocks = []
            for i in range(blocks):
                st.write(f"**Block {i+1}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    subj = st.text_input("Subject:", key=f"subj_{i}")
                with col2:
                    tm = st.time_input("Start:", value=time(9, 0), key=f"tm_{i}")
                with col3:
                    dur = st.selectbox("Duration:", ["30 min", "1 hour", "2 hours"], key=f"dur_{i}")
                
                topic = st.text_input("Topic:", key=f"top_{i}")
                
                if subj and topic:
                    study_blocks.append({
                        "subject": subj,
                        "start_time": tm.strftime("%H:%M"),
                        "duration": dur,
                        "topic": topic
                    })
                st.markdown("---")
            
            if st.button("💾 Save", use_container_width=True, key="save_sched", type="primary"):
                if not name:
                    st.error("Enter name!")
                elif not study_blocks:
                    st.error("Add blocks!")
                else:
                    data = {
                        "name": name,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "blocks": study_blocks
                    }
                    if save_schedule(data):
                        st.success("✅ Saved!")
                        st.balloons()
        
        with tab2:
            schedules = load_schedules()
            
            if not schedules:
                st.info("No schedules yet")
            else:
                for sched in schedules:
                    data = json.loads(sched["schedule_data"])
                    
                    with st.expander(f"📅 {data['name']}"):
                        st.write(f"**{data['start_date']} to {data['end_date']}**")
                        
                        for i, b in enumerate(data['blocks'], 1):
                            st.write(f"{i}. **{b['subject']}** - {b['start_time']} ({b['duration']})")
                            st.write(f"   {b['topic']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            txt = f"{data['name']}\n{data['start_date']} to {data['end_date']}\n\n"
                            for i, b in enumerate(data['blocks'], 1):
                                txt += f"{i}. {b['subject']} - {b['start_time']}\n   {b['topic']}\n\n"
                            
                            st.download_button("📥 Download", data=txt, file_name=f"{data['name']}.txt", key=f"dl_{sched['id']}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_{sched['id']}"):
                                if delete_schedule(sched['id']):
                                    st.success("Deleted!")
                                    st.rerun()
        
        with tab3:
            st.write("### 🤖 AI Generator")
            
            exam = st.date_input("Exam:", key="ai_exam")
            subjects = st.text_area("Subjects:", placeholder="Math\nPhysics", key="ai_subj")
            
            col1, col2 = st.columns(2)
            with col1:
                hrs = st.slider("Hours/day:", 1, 12, 4, key="ai_hrs")
            with col2:
                diff = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], key="ai_diff")
            
            prefs = st.text_area("Preferences:", placeholder="Morning person", key="ai_prefs")
            
            # BUTTON REPLACEMENT
            button_container = st.empty()
            
            if not st.session_state.is_generating:
                if button_container.button("🎯 Generate", use_container_width=True, key="gen_ai", type="primary"):
                    if not subjects:
                        st.error("Enter subjects!")
                    else:
                        st.session_state.is_generating = True
                        st.rerun()
            else:
                if button_container.button("⏹️ Stop", use_container_width=True, key="stop_ai", type="secondary"):
                    st.session_state.stop_generation = True
            
            if st.session_state.is_generating and subjects:
                st.markdown("---")
                response_placeholder = st.empty()
                
                days = (exam - datetime.now().date()).days
                
                prompt = f"""Study schedule:
- {days} days to exam
- Subjects: {subjects}
- {hrs} hours/day
- {diff} difficulty
- Prefs: {prefs if prefs else 'None'}

Include: Overview, Daily plan, Tips"""
                
                full_response = stream_response(prompt, response_placeholder)
                
                st.markdown("---")
                
                if "[⏹️" not in full_response:
                    st.download_button("📥 Download", data=full_response, file_name="ai_schedule.txt", key="dl_ai")
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"AI Schedule ({days}d)",
                            "answer": full_response
                        }).execute()
                
                st.session_state.is_generating = False
                st.rerun()

else:
    login_screen()
