import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta, time
import PIL.Image
import os
import json
import time as time_module

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

# --- 3. IMPROVED GEMINI INIT WITH RATE LIMIT HANDLING ---
@st.cache_resource
def initialize_gemini():
    """Auto-detects working model with rate limit awareness"""
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
        
        try:
            # List of models to try in order of preference
            models_to_try = [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
                "gemini-2.0-flash-exp"
            ]
            
            for model_name in models_to_try:
                try:
                    st.info(f"Testing: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    # Quick test with retry
                    for attempt in range(2):
                        try:
                            response = model.generate_content("Say ready")
                            if response.text:
                                st.success(f"🎉 CONNECTED: {model_name}")
                                return model
                        except Exception as e:
                            if "429" in str(e) or "quota" in str(e).lower():
                                st.warning(f"⚠️ {model_name} rate limited, trying next...")
                                break
                            if attempt == 0:
                                time_module.sleep(1)
                            else:
                                break
                except Exception as e:
                    if "429" not in str(e):
                        continue
            
            st.error("All models are rate limited or unavailable!")
            st.info("💡 Try again in a few minutes or upgrade your API quota")
            return None
            
        except Exception as e:
            st.error(f"Model detection failed: {e}")
            return None
            
    except Exception as e:
        st.error(f"Fatal error: {e}")
        return None

# --- 4. SMART AI CALL WITH RETRY & RATE LIMIT HANDLING ---
def safe_ai_call(model, prompt, max_retries=3, use_image=None):
    """
    Wrapper for AI calls with:
    - Automatic retry on transient errors
    - Rate limit detection and user-friendly messages
    - Exponential backoff
    """
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
            
            # Rate limit detection
            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                # Extract wait time if available
                wait_time = 60  # Default
                if "retry" in error_str.lower():
                    try:
                        # Try to extract seconds from error
                        import re
                        match = re.search(r'(\d+\.?\d*)\s*s', error_str)
                        if match:
                            wait_time = int(float(match.group(1))) + 1
                    except:
                        pass
                
                return None, f"⚠️ **Rate Limit Reached!**\n\n" \
                            f"Google's free tier allows 20 requests per day.\n\n" \
                            f"**Options:**\n" \
                            f"1. ⏰ Wait {wait_time} seconds and try again\n" \
                            f"2. 🔑 Upgrade your Google API plan\n" \
                            f"3. 📅 Use Schedule Planner (doesn't count towards limit)\n\n" \
                            f"💡 **Tip:** Premium features use fewer API calls!"
            
            # Other errors - retry with backoff
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2  # 2s, 4s, 6s
                time_module.sleep(wait)
            else:
                return None, f"Error after {max_retries} attempts: {error_str}"
    
    return None, "Unknown error occurred"

# Initialize
supabase = initialize_supabase()
model = initialize_gemini()

# --- 5. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "schedules" not in st.session_state:
    st.session_state.schedules = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_calls_today" not in st.session_state:
    st.session_state.api_calls_today = 0
if "last_reset" not in st.session_state:
    st.session_state.last_reset = datetime.now().date()

# --- 6. USAGE TRACKER WITH API CALL COUNTER ---
def get_daily_usage():
    """Counts all AI interactions in last 24 hours"""
    # Reset counter if new day
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
    """Increment API call counter"""
    st.session_state.api_calls_today += 1

# --- 7. CHAT HISTORY FUNCTIONS ---
def load_chat_history():
    """Load recent chat history from database"""
    if not supabase or not st.session_state.user:
        return []
    try:
        res = supabase.table("history").select("*").eq(
            "user_id", st.session_state.user.id
        ).order("created_at", desc=True).limit(20).execute()
        
        if res.data:
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

# --- 8. SCHEDULE MANAGEMENT FUNCTIONS ---
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
                        res = supabase.auth.sign_up({
                            "email": new_email, 
                            "password": new_pass
                        })
                        
                        if res.user:
                            st.session_state.user = res.user
                            st.success("🎉 Account created successfully!")
                            st.success("✅ You're now logged in!")
                            st.balloons()
                            time_module.sleep(1)
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

# --- 10. MAIN APP ---
if st.session_state.user:
    if not model:
        st.warning("⚠️ AI features temporarily unavailable")
        st.info("💡 You can still use the Schedule Planner feature!")
        
        # Show only schedule planner when AI unavailable
        st.sidebar.title("💎 Study Master Pro")
        st.sidebar.write(f"👋 Hey, **{st.session_state.user.email.split('@')[0]}**!")
        st.sidebar.warning("🤖 AI: Offline")
        
        if st.sidebar.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
        
        # Show schedule planner only
        st.subheader("📅 Study Schedule Planner")
        st.write("AI is temporarily unavailable, but you can still create and manage schedules!")
        
        # [Schedule planner code continues - same as before]
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
    
    # Usage Counter with API awareness
    usage = get_daily_usage()
    api_calls = st.session_state.api_calls_today
    limit = 250 if st.session_state.is_premium else 50
    
    st.sidebar.metric("Today's Usage", f"{usage}/{limit}")
    st.sidebar.caption(f"🤖 API Calls: {api_calls}/20 (Google Free Tier)")
    
    if api_calls >= 18:
        st.sidebar.warning(f"⚠️ Close to API limit!")
    
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
        st.session_state.api_calls_today = 0
        st.success("Logged out successfully!")
        st.rerun()
    
    # Check usage limit
    if usage >= limit and menu != "📅 Schedule Planner":
        st.error(f"⚠️ Daily limit reached ({usage}/{limit})")
        st.info("💎 **Upgrade to Premium** for 250 interactions/day!")
        st.stop()
    
    # Features with rate limit handling
    if menu == "💬 Chat":
        st.subheader("💬 AI Study Assistant")
        
        # Show API limit warning
        if api_calls >= 15:
            st.warning(f"⚠️ Google API: {api_calls}/20 calls used. Consider using Schedule Planner instead!")
        
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
        
        if st.session_state.chat_history:
            for msg in st.session_state.chat_history:
                with st.chat_message("user"):
                    st.write(msg.get("question", ""))
                with st.chat_message("assistant"):
                    st.write(msg.get("answer", ""))
        
        q = st.chat_input("Type your question...")
        
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
        
        if api_calls >= 15:
            st.warning(f"⚠️ API: {api_calls}/20 calls. Quiz generation uses 1 API call.")
        
        topic = st.text_input("Topic:", key="quiz_topic")
        
        col1, col2 = st.columns(2)
        with col1:
            difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard"], key="quiz_diff")
        with col2:
            num_questions = st.slider("Questions:", 3, 10, 5, key="quiz_num")
        
        if st.button("🎯 Generate Quiz", use_container_width=True, type="primary"):
            if not topic:
                st.error("Please enter a topic!")
            else:
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
                
                with st.spinner("Creating your quiz..."):
                    response_text, error = safe_ai_call(model, prompt)
                
                if response_text:
                    st.markdown("---")
                    st.markdown(response_text)
                    st.markdown("---")
                    
                    st.download_button(
                        "📥 Download Quiz",
                        data=response_text,
                        file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                        mime="text/plain"
                    )
                    
                    increment_usage()
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Quiz: {topic} ({difficulty})",
                            "answer": response_text
                        }).execute()
                else:
                    st.error(error)
    
    elif menu == "📁 Image":
        st.subheader("📁 Image Analysis")
        
        if api_calls >= 15:
            st.warning(f"⚠️ API: {api_calls}/20 calls. Image analysis uses 1 API call.")
        
        file = st.file_uploader("Upload image:", type=['jpg', 'png', 'jpeg'])
        
        if file:
            try:
                img = PIL.Image.open(file)
                st.image(img, caption="Your upload", use_container_width=True)
                
                if st.button("🔍 Analyze Image", use_container_width=True, type="primary"):
                    prompt = """Analyze this study material:
1. **Summary** - What is this?
2. **Key Concepts** - Main ideas
3. **Important Details** - Facts, formulas, dates
4. **Study Tips** - How to remember
5. **Practice Questions** - 2-3 test questions"""
                    
                    with st.spinner("Analyzing..."):
                        response_text, error = safe_ai_call(model, prompt, use_image=img)
                    
                    if response_text:
                        st.markdown("---")
                        st.markdown(response_text)
                        st.markdown("---")
                        
                        increment_usage()
                        if supabase:
                            supabase.table("history").insert({
                                "user_id": st.session_state.user.id,
                                "question": "Image Analysis",
                                "answer": response_text
                            }).execute()
                    else:
                        st.error(error)
                        
            except Exception as e:
                st.error(f"Error: {e}")
    
    elif menu == "🎯 Tutor":
        st.subheader("🎯 Socratic Tutor")
        st.info("💡 Learn through guided questions!")
        
        if api_calls >= 15:
            st.warning(f"⚠️ API: {api_calls}/20 calls remaining")
        
        problem = st.text_area("Describe your problem:", height=150)
        
        if st.button("🚀 Start Session", use_container_width=True, type="primary"):
            if not problem:
                st.error("Please describe your problem!")
            else:
                prompt = f"""Act as a Socratic tutor for: "{problem}"

Do NOT give the answer. Instead:
1. Ask 3-4 guiding questions
2. Help them discover the answer
3. Encourage critical thinking

Start with: "Let me help you think through this..."
"""
                
                with st.spinner("Preparing questions..."):
                    response_text, error = safe_ai_call(model, prompt)
                
                if response_text:
                    st.markdown("---")
                    st.markdown(response_text)
                    st.markdown("---")
                    
                    increment_usage()
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": f"Socratic: {problem}",
                            "answer": response_text
                        }).execute()
                else:
                    st.error(error)
    
    elif menu == "📅 Schedule Planner":
        st.subheader("📅 Study Schedule Planner")
        st.success("✨ No API calls needed - unlimited use!")
        
        tab1, tab2, tab3 = st.tabs(["➕ Create Schedule", "📋 My Schedules", "🤖 AI Generator"])
        
        with tab1:
            st.write("### Manual Schedule Creation")
            
            schedule_name = st.text_input("Schedule Name:", placeholder="e.g., Final Exams Week")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date:")
            with col2:
                end_date = st.date_input("End Date:")
            
            st.write("### Add Study Blocks")
            
            num_blocks = st.number_input("Number of study blocks:", 1, 10, 3)
            
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
                
                topic = st.text_input(f"Topic/Task:", key=f"topic_{i}", placeholder="e.g., Chapter 5")
                
                if subject and topic:
                    study_blocks.append({
                        "subject": subject,
                        "start_time": start_time.strftime("%H:%M"),
                        "duration": duration,
                        "topic": topic
                    })
                
                st.markdown("---")
            
            if st.button("💾 Save Schedule", use_container_width=True, type="primary"):
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
                st.info("📅 No schedules yet. Create one!")
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
            
            if api_calls >= 18:
                st.error("⚠️ Too close to API limit! Try manual schedule creation instead.")
            else:
                st.info(f"💡 This uses 1 API call ({api_calls}/20 used today)")
                
                exam_date = st.date_input("Exam/Deadline Date:")
                subjects = st.text_area("Subjects (one per line):", 
                                        placeholder="Math\nPhysics\nChemistry")
                
                col1, col2 = st.columns(2)
                with col1:
                    hours_per_day = st.slider("Study hours per day:", 1, 12, 4)
                with col2:
                    difficulty = st.selectbox("Overall difficulty:", ["Easy", "Medium", "Hard"])
                
                preferences = st.text_area("Special preferences (optional):", 
                                           placeholder="e.g., Morning person, need breaks")
                
                if st.button("🎯 Generate AI Schedule", use_container_width=True, type="primary"):
                    if not subjects:
                        st.error("Please enter subjects!")
                    else:
                        days_until_exam = (exam_date - datetime.now().date()).days
                        
                        prompt = f"""Create a study schedule:

- Exam: {days_until_exam} days away
- Subjects: {subjects}
- Daily hours: {hours_per_day}
- Difficulty: {difficulty}
- Preferences: {preferences if preferences else 'None'}

Provide:
1. **Overview** - Strategy
2. **Daily Breakdown** - Time blocks
3. **Tips** - Study techniques
4. **Revision Plan** - Review schedule

Be realistic!"""
                        
                        with st.spinner("AI creating your schedule..."):
                            response_text, error = safe_ai_call(model, prompt)
                        
                        if response_text:
                            st.markdown("---")
                            st.markdown(response_text)
                            st.markdown("---")
                            
                            st.download_button(
                                "📥 Download AI Schedule",
                                data=response_text,
                                file_name="ai_study_schedule.txt",
                                mime="text/plain"
                            )
                            
                            increment_usage()
                            if supabase:
                                supabase.table("history").insert({
                                    "user_id": st.session_state.user.id,
                                    "question": f"AI Schedule: {subjects.split()[0]}...",
                                    "answer": response_text
                                }).execute()
                        else:
                            st.error(error)

else:
    login_screen()
   
    # Add this in the sidebar
with st.sidebar:
    st.header("Study Settings")
    subject = st.selectbox("Choose a Subject", ["General", "Math", "Science", "History", "Coding"])
    language = st.selectbox("Choose a Language", ["English", "Spanish", "Hindi", "French", "German"])

# Then, update the prompt to include these choices
if prompt:
    # We tell the AI what subject and language to use
    full_prompt = f"Act as a {subject} expert. Respond in {language}. Question: {prompt}"
    response = model.generate_content(full_prompt)
    st.markdown(response.text)
