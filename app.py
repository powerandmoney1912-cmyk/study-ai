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
            
            # Try each model
            for model_info in valid_models:
                model_name = model_info.name
                
                # Try full name
                try:
                    st.info(f"Testing: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content("Say ready")
                    if response.text:
                        st.success(f"🎉 CONNECTED: {model_name}")
                        return model
                except:
                    pass
                
                # Try short name
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
if "schedules" not in st.session_state:
    st.session_state.schedules = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 5. USAGE TRACKER ---
def get_daily_usage():
    """Counts all AI interactions in last 24 hours"""
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
    """Load recent chat history from database"""
    if not supabase or not st.session_state.user:
        return []
    try:
        res = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(20).execute()
        
        if res.data:
            # Reverse to show oldest first
            return list(reversed(res.data))
        return []
    except:
        return []

def save_chat_message(question, answer):
    """Save chat message to database"""
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
    """Clear all chat history for user"""
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

# --- 7. SCHEDULE MANAGEMENT FUNCTIONS ---
def save_schedule(schedule_data):
    """Save schedule to Supabase"""
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
    except Exception as e:
        st.error(f"Failed to save schedule: {e}")
        return False

def load_schedules():
    """Load user's schedules from Supabase"""
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
    """Delete a schedule"""
    if not supabase:
        return False
    try:
        supabase.table("schedules").delete().eq("id", schedule_id).execute()
        return True
    except:
        return False

# --- 8. IMPROVED LOGIN SCREEN (AUTO-LOGIN AFTER SIGNUP) ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    # Show features
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💬 **AI Chat**\nAsk anything!")
    with col2:
        st.info("📝 **Quiz Gen**\nCustom quizzes")
    with col3:
        st.info("📅 **Planner**\nStudy schedules")
    
    if not supabase:
        st.error("Connection failed. Check Supabase settings.")
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
                    st.success("✅ Logged in successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")
            else:
                st.error("Please enter both email and password")
    
    with tab2:
        st.write("### Create Your Account")
        st.info("🎁 Get 50 free AI interactions daily!")
        
        new_email = st.text_input("Email Address", key="s_email", 
                                   placeholder="student@example.com")
        new_pass = st.text_input("Password (min 6 characters)", 
                                  type="password", key="s_pass")
        confirm_pass = st.text_input("Confirm Password", 
                                      type="password", key="s_confirm")
        
        # Terms checkbox
        agree = st.checkbox("I agree to the Terms of Service", key="agree")
        
        if st.button("🎉 Create Account", use_container_width=True, type="primary"):
            if not new_email or not new_pass:
                st.error("❌ Please fill in all fields")
            elif len(new_pass) < 6:
                st.error("❌ Password must be at least 6 characters")
            elif new_pass != confirm_pass:
                st.error("❌ Passwords don't match")
            elif not agree:
                st.error("❌ Please agree to Terms of Service")
            else:
                try:
                    with st.spinner("Creating your account..."):
                        # Sign up the user
                        res = supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_pass
                        })
                        
                        # Check if email confirmation is required
                        if res.user:
                            # AUTO-LOGIN: Set user in session
                            st.session_state.user = res.user
                            
                            st.success("🎉 Account created successfully!")
                            st.success("✅ You're now logged in!")
                            st.balloons()
                            
                            # Small delay then rerun
                            import time
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.success("✅ Account created!")
                            st.info("📧 Please check your email to verify your account, then log in.")
                            
                except Exception as e:
                    error_msg = str(e)
                    if "already registered" in error_msg.lower():
                        st.error("❌ This email is already registered. Please log in.")
                    else:
                        st.error(f"❌ Signup failed: {error_msg}")

# --- 9. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("⚠️ AI unavailable. Check errors above.")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master Pro")
    st.sidebar.write(f"👋 Hey, **{st.session_state.user.email.split('@')[0]}**!")
    
    # Premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("⭐ Upgrade to Premium"):
            st.write("**Premium Benefits:**")
            st.write("✅ 250 AI uses/day (vs 50)")
            st.write("✅ Unlimited schedules")
            st.write("✅ Priority support")
            st.write("✅ Early access to features")
            code = st.text_input("Enter Code", type="password", key="prem")
            if st.button("Activate Premium", key="activate_premium"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("🎉 Premium Activated!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Invalid code")
    else:
        st.sidebar.success("⭐ Premium Member")
    
    # Usage Counter
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    
    if usage >= limit:
        st.sidebar.error(f"🚫 Limit: {usage}/{limit}")
    else:
        st.sidebar.metric("Today's Usage", f"{usage}/{limit}")
    
    st.sidebar.progress(min(usage/limit, 1.0))
    st.sidebar.caption("⏰ Resets every 24 hours")
    
    # Menu
    menu = st.sidebar.radio("📚 Navigation", [
        "💬 Chat", 
        "📝 Quiz", 
        "📁 Image", 
        "🎯 Tutor",
        "📅 Schedule Planner"
    ])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.chat_history = []
        st.success("Logged out successfully!")
        st.rerun()
    
    # Check usage limit
    if usage >= limit and menu != "📅 Schedule Planner":
        st.error(f"⚠️ Daily limit reached ({usage}/{limit})")
        st.info("💎 **Upgrade to Premium** for 250 interactions/day!")
        st.info("⏰ Or wait for your 24-hour reset")
        st.stop()
    
    # Features
    if menu == "💬 Chat":
        st.subheader("💬 AI Study Assistant")
        
        # Chat controls
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write("Ask me anything about your studies!")
        with col2:
            if st.button("📜 Load History", key="load_hist"):
                st.session_state.chat_history = load_chat_history()
                st.success("History loaded!")
        with col3:
            if st.button("🗑️ Clear Chat", key="clear_hist"):
                if clear_chat_history():
                    st.success("Chat cleared!")
                    st.rerun()
        
        st.markdown("---")
        
        # Display chat history
        if st.session_state.chat_history:
            for msg in st.session_state.chat_history:
                with st.chat_message("user"):
                    st.write(msg.get("question", ""))
                with st.chat_message("assistant"):
                    st.write(msg.get("answer", ""))
        
        # Chat input
        q = st.chat_input("Type your question...")
        
        if q:
            # Display user message
            with st.chat_message("user"):
                st.write(q)
            
            try:
                with st.spinner("Thinking..."):
                    resp = model.generate_content(q)
                
                # Display AI response
                with st.chat_message("assistant"):
                    st.write(resp.text)
                
                # Save to database and session
                if save_chat_message(q, resp.text):
                    st.session_state.chat_history.append({
                        "question": q,
                        "answer": resp.text,
                        "created_at": datetime.now().isoformat()
                    })
                
            except Exception as e:
                st.error(f"Error: {e}")
    
    elif menu == "📝 Quiz":
        st.subheader("📝 Quiz Generator")
        st.write("Create custom quizzes on any topic!")
        
        topic = st.text_input("Topic (e.g., World War 2, Photosynthesis):", key="quiz_topic")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], key="quiz_diff")
        with col2:
            num_questions = st.slider("Questions:", 3, 10, 5, key="quiz_num")
        
        if st.button("🎯 Generate Quiz", use_container_width=True, key="generate_quiz_btn", type="primary"):
            if not topic:
                st.error("Please enter a topic!")
            else:
                try:
                    with st.spinner("Creating your quiz..."):
                        prompt = f"""Create a {num_questions}-question multiple choice quiz about {topic} at {difficulty} difficulty level.

Format:
**Question 1:** [question]
A) [option]
B) [option]
C) [option]
D) [option]

[repeat for all questions]

**Answer Key:**
1. [correct letter]
2. [correct letter]
etc."""
                        resp = model.generate_content(prompt)
                    
                    st.markdown("---")
                    st.markdown(resp.text)
                    st.markdown("---")
                    
                    st.download_button(
                        label="📥 Download Quiz",
                        data=resp.text,
                        file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                        mime="text/plain",
                        key="download_quiz"
                    )
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Quiz: {topic} ({difficulty})",
                            "answer": resp.text
                        }).execute()
                        
                except Exception as e:
                    st.error(f"Error: {e}")
    
    elif menu == "📁 Image":
        st.subheader("📁 Image Analysis")
        st.write("Upload study materials for AI analysis")
        
        file = st.file_uploader("Upload image:", type=['jpg', 'png', 'jpeg'], key="image_upload")
        
        if file:
            try:
                img = PIL.Image.open(file)
                st.image(img, caption="Your upload", use_container_width=True)
                
                if st.button("🔍 Analyze Image", use_container_width=True, key="analyze_img_btn", type="primary"):
                    with st.spinner("Analyzing..."):
                        resp = model.generate_content([
                            """Analyze this study material:
1. **Summary** - What is this?
2. **Key Concepts** - Main ideas
3. **Important Details** - Facts, formulas, dates
4. **Study Tips** - How to remember
5. **Practice Questions** - 2-3 test questions""",
                            img
                        ])
                    
                    st.markdown("---")
                    st.markdown(resp.text)
                    st.markdown("---")
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": "Image Analysis",
                            "answer": resp.text
                        }).execute()
                        
            except Exception as e:
                st.error(f"Error: {e}")
    
    elif menu == "🎯 Tutor":
        st.subheader("🎯 Socratic Tutor")
        st.info("💡 Learn through guided questions, not direct answers!")
        
        problem = st.text_area("Describe your problem:", height=150, key="tutor_problem")
        
        if st.button("🚀 Start Session", use_container_width=True, key="start_tutor_btn", type="primary"):
            if not problem:
                st.error("Please describe your problem!")
            else:
                try:
                    with st.spinner("Preparing questions..."):
                        resp = model.generate_content(f"""Act as a Socratic tutor for: "{problem}"

Do NOT give the answer. Instead:
1. Ask 3-4 guiding questions
2. Help them discover the answer
3. Encourage critical thinking
4. Be supportive

Start with: "Let me help you think through this..."
""")
                    
                    st.markdown("---")
                    st.markdown(resp.text)
                    st.markdown("---")
                    
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Socratic: {problem}",
                            "answer": resp.text
                        }).execute()
                        
                except Exception as e:
                    st.error(f"Error: {e}")
    
    elif menu == "📅 Schedule Planner":
        st.subheader("📅 Study Schedule Planner")
        st.write("Create and manage your study schedule")
        
        tab1, tab2, tab3 = st.tabs(["➕ Create Schedule", "📋 My Schedules", "🤖 AI Generator"])
        
        with tab1:
            st.write("### Manual Schedule Creation")
            
            schedule_name = st.text_input("Schedule Name:", placeholder="e.g., Final Exams Week", key="sched_name")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date:", key="start_date")
            with col2:
                end_date = st.date_input("End Date:", key="end_date")
            
            st.write("### Add Study Blocks")
            
            num_blocks = st.number_input("Number of study blocks:", 1, 10, 3, key="num_blocks")
            
            study_blocks = []
            for i in range(num_blocks):
                st.write(f"**Block {i+1}**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    subject = st.text_input(f"Subject:", key=f"subject_{i}", placeholder="e.g., Math")
                with col2:
                    start_time = st.time_input(f"Start:", value=time(9, 0), key=f"start_{i}")
                with col3:
                    duration = st.selectbox(f"Duration:", ["30 min", "1 hour", "1.5 hours", "2 hours"], key=f"dur_{i}")
                
                topic = st.text_input(f"Topic/Task:", key=f"topic_{i}", placeholder="e.g., Chapter 5 - Calculus")
                
                if subject and topic:
                    study_blocks.append({
                        "subject": subject,
                        "start_time": start_time.strftime("%H:%M"),
                        "duration": duration,
                        "topic": topic
                    })
                
                st.markdown("---")
            
            if st.button("💾 Save Schedule", use_container_width=True, key="save_schedule", type="primary"):
                if not schedule_name:
                    st.error("Please enter a schedule name!")
                elif not study_blocks:
                    st.error("Please add at least one study block!")
                else:
                    schedule_data = {
                        "name": schedule_name,
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "blocks": study_blocks,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    if save_schedule(schedule_data):
                        st.success("✅ Schedule saved successfully!")
                        st.balloons()
                    else:
                        st.error("Failed to save schedule")
        
        with tab2:
            st.write("### Your Saved Schedules")
            
            schedules = load_schedules()
            
            if not schedules:
                st.info("📅 No schedules yet. Create one in the 'Create Schedule' tab!")
            else:
                for schedule in schedules:
                    schedule_data = json.loads(schedule["schedule_data"])
                    
                    with st.expander(f"📅 {schedule_data['name']}", expanded=False):
                        st.write(f"**Period:** {schedule_data['start_date']} to {schedule_data['end_date']}")
                        st.write(f"**Created:** {schedule['created_at'][:10]}")
                        
                        st.write("### Study Blocks:")
                        for i, block in enumerate(schedule_data['blocks'], 1):
                            st.write(f"**{i}. {block['subject']}** - {block['start_time']} ({block['duration']})")
                            st.write(f"   📖 {block['topic']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            text = f"{schedule_data['name']}\n"
                            text += f"Period: {schedule_data['start_date']} to {schedule_data['end_date']}\n\n"
                            for i, block in enumerate(schedule_data['blocks'], 1):
                                text += f"{i}. {block['subject']} - {block['start_time']} ({block['duration']})\n"
                                text += f"   Topic: {block['topic']}\n\n"
                            
                            st.download_button(
                                "📥 Download",
                                data=text,
                                file_name=f"{schedule_data['name']}.txt",
                                key=f"dl_{schedule['id']}"
                            )
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_{schedule['id']}"):
                                if delete_schedule(schedule['id']):
                                    st.success("Deleted!")
                                    st.rerun()
        
        with tab3:
            st.write("### 🤖 AI-Powered Schedule Generator")
            st.info("Let AI create an optimized study schedule for you!")
            
            exam_date = st.date_input("Exam/Deadline Date:", key="ai_exam_date")
            subjects = st.text_area("Subjects to study (one per line):", 
                                    placeholder="Math\nPhysics\nChemistry\nBiology", 
                                    key="ai_subjects")
            
            col1, col2 = st.columns(2)
            with col1:
                hours_per_day = st.slider("Study hours per day:", 1, 12, 4, key="ai_hours")
            with col2:
                difficulty = st.selectbox("Overall difficulty:", ["Easy", "Medium", "Hard"], key="ai_diff")
            
            preferences = st.text_area("Special preferences (optional):", 
                                       placeholder="e.g., I'm a morning person, need breaks every hour",
                                       key="ai_prefs")
            
            if st.button("🎯 Generate AI Schedule", use_container_width=True, key="gen_ai_schedule", type="primary"):
                if not subjects:
                    st.error("Please enter subjects!")
                else:
                    try:
                        with st.spinner("AI is creating your personalized schedule..."):
                            days_until_exam = (exam_date - datetime.now().date()).days
                            
                            prompt = f"""Create a detailed study schedule with these parameters:

- Exam/Deadline: {days_until_exam} days from now
- Subjects: {subjects}
- Daily study time: {hours_per_day} hours
- Difficulty level: {difficulty}
- Preferences: {preferences if preferences else 'None'}

Provide:
1. **Overview** - Study strategy summary
2. **Daily Breakdown** - What to study each day with time blocks
3. **Tips** - Study techniques and time management advice
4. **Revision Plan** - When to review each subject

Make it realistic and achievable!"""
                            
                            resp = model.generate_content(prompt)
                        
                        st.markdown("---")
                        st.markdown(resp.text)
                        st.markdown("---")
                        
                        st.download_button(
                            "📥 Download AI Schedule",
                            data=resp.text,
                            file_name="ai_study_schedule.txt",
                            mime="text/plain",
                            key="download_ai_schedule"
                        )
                        
                        # Save to history (counts towards usage)
                        if supabase:
                            supabase.table("history").insert({
                                "user_id": st.session_state.user.id,
                                "question": f"AI Schedule: {subjects.split()[0]}... ({days_until_exam} days)",
                                "answer": resp.text
                            }).execute()
                        
                    except Exception as e:
                        st.error(f"Error: {e}")

else:
    login_screen()
