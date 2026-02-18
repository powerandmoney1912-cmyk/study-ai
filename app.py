import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time
import base64
import io
from PIL import Image

# --- 1. CORE SETUP ---
st.set_page_config(
    page_title="Study Master Infinity - Free AI Study Assistant",
    layout="wide",
    page_icon="🎓",
    initial_sidebar_state="expanded"
)

# Google Search Console Verification + SEO Meta Tags
st.markdown("""
<head>
    <meta name="google-site-verification" content="ThWp6_7rt4Q973HycJ07l-jYZ0o55s8f0Em28jBBNoU" />
    <meta name="description" content="Study Master Infinity - Free AI study assistant with chat, quiz generator, teacher mode, image analysis and study planner. Powered by Groq AI.">
    <meta name="keywords" content="study master infinity, study master, AI study tool, free study assistant, AI tutor, quiz generator, study planner, groq ai, free education tool">
    <meta name="author" content="Aarya">
    <meta property="og:title" content="Study Master Infinity - Free AI Study Assistant">
    <meta property="og:description" content="Chat with AI, generate quizzes, get tested and graded, analyze images - all free!">
    <meta property="og:type" content="website">
    <meta property="og:image" content="🎓">
</head>
""", unsafe_allow_html=True)

# Initialize APIs
try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except Exception as e:
    st.error(f"⚠️ API Keys missing! Error: {e}")
    st.info("Add these to Streamlit Secrets:")
    st.code("""
[supabase]
url = "your-supabase-url"
key = "your-supabase-key"

GROQ_API_KEY = "your-groq-key"
    """)
    st.stop()

# --- 2. AUTH & USERNAME ---
if "user" not in st.session_state:
    # Login/Signup Screen
    st.title("🎓 Study Master Infinity")
    st.subheader("⚡ Powered by Groq - Ultra Fast AI")
    
    # Feature showcase
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("💬 **Smart Chat**\nAI remembers context")
    with col2:
        st.info("👨‍🏫 **Teacher Mode**\nGet tested & graded")
    with col3:
        st.info("📊 **Track Progress**\nEarn XP & level up")
    
    st.markdown("---")
    
    t1, t2 = st.tabs(["🔑 Login", "✨ Create Account"])
    
    # LOGIN TAB
    with t1:
        st.write("### Welcome Back!")
        
        login_email = st.text_input("📧 Email", key="login_email", placeholder="your@email.com")
        login_pass = st.text_input("🔒 Password", type="password", key="login_pass", placeholder="Enter your password")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🚀 Log In", use_container_width=True, type="primary", key="login_btn"):
                if login_email and login_pass:
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
                    except Exception as err:
                        error_msg = str(err)
                        if "Invalid login credentials" in error_msg:
                            st.error("❌ Invalid email or password!")
                        elif "Email not confirmed" in error_msg:
                            st.error("❌ Please verify your email first!")
                        else:
                            st.error(f"❌ Login failed: {error_msg}")
                else:
                    st.warning("⚠️ Please enter both email and password")
        
        with col2:
            st.write("")  # Spacing
    
    # SIGNUP TAB
    with t2:
        st.write("### Create Your Free Account")
        st.info("🎁 Join now and start learning with AI!")
        
        signup_email = st.text_input("📧 Email Address", key="signup_email", placeholder="your@email.com")
        
        col1, col2 = st.columns(2)
        with col1:
            signup_pass = st.text_input("🔒 Password", type="password", key="signup_pass", placeholder="Min 6 characters")
        with col2:
            confirm_pass = st.text_input("🔒 Confirm Password", type="password", key="signup_confirm", placeholder="Re-enter password")
        
        # Terms checkbox
        agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy", key="agree_terms")
        
        if st.button("🎉 Create Account", use_container_width=True, type="primary", key="signup_btn"):
            # Validation
            if not signup_email:
                st.error("❌ Please enter your email address")
            elif not signup_pass:
                st.error("❌ Please enter a password")
            elif len(signup_pass) < 6:
                st.error("❌ Password must be at least 6 characters long")
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
                            
                            # Auto-login if email confirmation not required
                            if res.user.email_confirmed_at:
                                st.session_state.user = res.user
                                st.success("🎉 You're now logged in!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.warning("⚠️ Please verify your email, then login above")
                        else:
                            st.error("❌ Account creation failed. Please try again.")
                            
                except Exception as err:
                    error_msg = str(err)
                    if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
                        st.error("❌ This email is already registered! Please login instead.")
                    elif "invalid email" in error_msg.lower():
                        st.error("❌ Invalid email address format!")
                    else:
                        st.error(f"❌ Signup error: {error_msg}")
    
    st.markdown("---")
    st.caption("🔐 Your data is encrypted and secure")
    st.stop()

# Check/Create Profile with Username
try:
    profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
    
    if not profile_res.data:
        # Username Setup Screen
        st.title("🎨 Complete Your Profile")
        st.write("### Choose Your Username")
        st.info("💡 This is how you'll appear in the app!")

        import re

        def is_valid_username(name):
            """Allow letters (including Tamil/Unicode), numbers, _ and -"""
            return bool(re.match(r'^[\w\-]{3,20}$', name, re.UNICODE))

        username_input = st.text_input(
            "👤 Username",
            placeholder="e.g., Seashore, Kandasamy, StarLearner",
            max_chars=20,
            key="username_setup"
        )

        # Live validation feedback
        if username_input:
            if len(username_input) < 3:
                st.warning("⚠️ Username must be at least 3 characters")
            elif len(username_input) > 20:
                st.warning("⚠️ Username too long (max 20 characters)")
            elif not is_valid_username(username_input):
                st.warning("⚠️ No spaces or special characters allowed")
            else:
                st.success("✅ Username looks good!")

        # Avatar selection
        st.write("### Pick Your Avatar")
        avatar_options = ["🎓", "📚", "🧠", "⚡", "🌟", "🚀", "💎", "🔥", "👑", "🎯"]
        selected_avatar = st.selectbox("Choose an emoji:", avatar_options, key="avatar_select")

        st.markdown("---")

        if st.button("💾 Save & Continue", use_container_width=True, type="primary"):
            if not username_input:
                st.error("❌ Please enter a username")
            elif len(username_input) < 3:
                st.error("❌ Username must be at least 3 characters")
            elif len(username_input) > 20:
                st.error("❌ Username too long (max 20 characters)")
            elif not is_valid_username(username_input):
                st.error("❌ No spaces or special characters allowed")
            else:
                try:
                    # Check if username is taken
                    existing = supabase.table("profiles").select("id").eq("username", username_input).execute()

                    if existing.data:
                        st.error("❌ Username already taken! Try another one.")
                    else:
                        # Try inserting with avatar first, fallback without if column missing
                        try:
                            supabase.table("profiles").insert({
                                "id": st.session_state.user.id,
                                "username": username_input,
                                "avatar": selected_avatar,
                                "xp": 0,
                                "is_premium": False,
                                "created_at": datetime.now().isoformat()
                            }).execute()
                        except Exception:
                            # Fallback: insert without avatar column
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
                    error_msg = str(e)
                    # Show clean error messages
                    if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                        st.error("❌ Username already taken! Try another one.")
                    elif "foreign key" in error_msg.lower():
                        st.error("❌ Session expired. Please log out and log in again.")
                    else:
                        st.error(f"❌ Error: {error_msg}")

        st.caption("💡 Examples: Seashore, Kandasamy, StarLearner, MathWizard")
        st.stop()
    
    user_data = profile_res.data[0]
except Exception as e:
    st.error(f"❌ Profile error: {e}")
    user_data = {"username": "User", "avatar": "🎓", "xp": 0, "is_premium": False}

# --- 3. SIDEBAR ---
with st.sidebar:
    # User header with avatar
    avatar = user_data.get('avatar', '🎓')
    username = user_data.get('username', 'User')
    
    st.markdown(f"# {avatar} {username}")
    
    # Level and XP
    xp = user_data.get('xp', 0)
    level = xp // 100 + 1
    xp_in_level = xp % 100
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("📊 Level", level)
    with col2:
        st.metric("⭐ XP", xp)
    
    st.progress(xp_in_level / 100)
    st.caption(f"{xp_in_level}/100 XP to Level {level + 1}")
    
    st.markdown("---")
    
    # Premium
    if not user_data.get('is_premium'):
        with st.expander("⭐ Unlock Premium"):
            st.write("**Benefits:**")
            st.write("✅ Unlimited AI calls")
            st.write("✅ Advanced features")
            st.write("✅ Priority support")
            p_code = st.text_input("Premium Code", type="password", key="premium_code")
            if st.button("Activate Premium"):
                if p_code == "STUDY777":
                    try:
                        supabase.table("profiles").update({"is_premium": True}).eq("id", st.session_state.user.id).execute()
                        st.success("💎 Premium Unlocked!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    except:
                        st.error("Activation failed")
                else:
                    st.error("Invalid code")
    else:
        st.success("💎 PREMIUM ACTIVE")
    
    st.markdown("---")
    
    # Menu
    menu = st.radio("📚 Features", [
        "💬 Chat",
        "📝 Quiz Generator", 
        "📅 Schedule Planner",
        "👨‍🏫 Teacher Mode",
        "📸 Image Analysis",
        "🗂️ Flashcards",
        "📊 Dashboard"
    ])
    
    st.markdown("---")
    
    # Language
    lang = st.selectbox("🌍 Language", [
        "English",
        "Tamil (தமிழ்)",
        "Hindi (हिंदी)",
        "Spanish (Español)"
    ])
    
    st.markdown("---")
    st.caption("✨ Made by Aarya")
    st.caption("⚡ Powered by Groq")
    
    if st.button("🚪 Logout", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except:
            pass
        del st.session_state.user
        st.rerun()

# --- 4. AI HELPER WITH MEMORY ---
def ask_ai(prompt, system_role="Expert Study Assistant", include_memory=True):
    """Call Groq AI with optional conversation memory"""
    try:
        # Build context with memory if enabled
        messages = []
        
        if include_memory:
            # Fetch last 5 conversations for context
            try:
                past = supabase.table("history").select("role, content").eq(
                    "user_id", st.session_state.user.id
                ).order("created_at", desc=True).limit(10).execute()
                
                # Add past messages (reversed to chronological order)
                for msg in reversed(past.data):
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            except:
                pass
        
        # Extract language
        lang_name = lang.split("(")[0].strip()
        
        # System message
        system_msg = f"{system_role}. Always respond in {lang_name}. Be helpful, clear, and educational."
        messages.insert(0, {"role": "system", "content": system_msg})
        
        # Add current user prompt
        messages.append({"role": "user", "content": prompt})
        
        # Call Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}\n\nPlease try again or check your API key."

# --- 5. FEATURE MODULES ---

if menu == "💬 Chat":
    st.header("💬 AI Study Chat")
    st.caption("⚡ Lightning-fast responses with Groq")
    
    # Initialize chat messages in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Load history from database
        try:
            hist = supabase.table("history").select("*").eq(
                "user_id", st.session_state.user.id
            ).order("created_at").execute()
            
            if hist.data:
                st.session_state.messages = [
                    {"role": m.get("role", "assistant"), "content": m.get("content", "")}
                    for m in hist.data
                ]
        except:
            st.session_state.messages = []
    
    # Chat controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write("💡 Ask anything about your studies!")
    with col2:
        if st.button("🔄 Reload", key="reload_chat"):
            try:
                hist = supabase.table("history").select("*").eq(
                    "user_id", st.session_state.user.id
                ).order("created_at").execute()
                
                st.session_state.messages = [
                    {"role": m.get("role", "assistant"), "content": m.get("content", "")}
                    for m in hist.data
                ]
                st.success("✅ Reloaded!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Reload failed: {e}")
    
    with col3:
        if st.button("🗑️ Clear", key="clear_chat"):
            try:
                supabase.table("history").delete().eq("user_id", st.session_state.user.id).execute()
                st.session_state.messages = []
                st.success("✅ Cleared!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Clear failed: {e}")
    
    st.markdown("---")
    
    # Display all messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your question here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Save user message to database
        try:
            supabase.table("history").insert({
                "user_id": st.session_state.user.id,
                "role": "user",
                "content": prompt,
                "created_at": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            st.error(f"Failed to save: {e}")
        
        # Get AI response
        with st.spinner("🤔 Thinking..."):
            try:
                answer = ask_ai(prompt, include_memory=True)
            except Exception as e:
                answer = f"⚠️ Error: {str(e)}"
        
        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": answer})
        
        # Display assistant response
        with st.chat_message("assistant"):
            st.write(answer)
        
        # Save AI response to database and award XP
        try:
            supabase.table("history").insert({
                "user_id": st.session_state.user.id,
                "role": "assistant",
                "content": answer,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            # Award XP (5 points per message)
            current_xp = user_data.get('xp', 0)
            supabase.table("profiles").update({
                "xp": current_xp + 5
            }).eq("id", st.session_state.user.id).execute()
        except Exception as e:
            pass  # Silently fail on XP/save errors
        
        # Rerun to update the display
        st.rerun()

elif menu == "📝 Quiz Generator":
    st.header("📝 Instant Quiz Generator")
    st.write("Create custom quizzes on any topic!")
    
    topic = st.text_input("📚 Topic:", placeholder="e.g., World War 2, Photosynthesis")
    
    col1, col2 = st.columns(2)
    with col1:
        difficulty = st.selectbox("🎯 Difficulty:", ["Easy", "Medium", "Hard", "Expert"])
    with col2:
        num_q = st.slider("❓ Number of questions:", 3, 10, 5)
    
    if st.button("🎯 Generate Quiz", use_container_width=True, type="primary"):
        if topic:
            prompt = f"""Create a {num_q}-question multiple choice quiz about {topic} at {difficulty} level.

Format each question like this:
**Question 1:** [question text]
A) [option]
B) [option]
C) [option]
D) [option]

**Answer Key:**
1. [correct letter]
2. [correct letter]
etc.

**Explanations:**
1. [brief explanation why the answer is correct]
etc."""
            
            with st.spinner("🎨 Creating your quiz..."):
                quiz = ask_ai(prompt, include_memory=False)
            
            st.markdown("---")
            st.markdown(quiz)
            st.markdown("---")
            
            st.download_button(
                "📥 Download Quiz",
                quiz,
                file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                mime="text/plain"
            )
        else:
            st.error("Please enter a topic!")

elif menu == "📅 Schedule Planner":
    st.header("📅 AI Study Schedule Generator")
    st.write("Let AI create a personalized study plan!")
    
    subjects = st.text_area("📚 Subjects to study:", 
                            placeholder="Math\nPhysics\nChemistry\nBiology",
                            height=100)
    
    col1, col2 = st.columns(2)
    with col1:
        days = st.number_input("📆 Days until exam:", 1, 365, 30)
    with col2:
        hours_day = st.slider("⏰ Study hours per day:", 1, 12, 4)
    
    focus = st.text_input("🎯 Focus areas (optional):", 
                         placeholder="e.g., weak in calculus, need more practice in organic chemistry")
    
    if st.button("🚀 Generate Schedule", use_container_width=True, type="primary"):
        if subjects:
            prompt = f"""Create a detailed {days}-day study schedule for these subjects:
{subjects}

Study time: {hours_day} hours/day
Focus areas: {focus if focus else 'None'}

Provide:
1. **Daily Breakdown** - What to study each day with specific time blocks
2. **Weekly Goals** - Milestones for each week
3. **Revision Strategy** - When and how to review
4. **Tips** - Study techniques and time management advice

Make it realistic and achievable!"""
            
            with st.spinner("🎨 Creating your study plan..."):
                schedule = ask_ai(prompt, include_memory=False)
            
            st.markdown("---")
            st.markdown(schedule)
            st.markdown("---")
            
            st.download_button(
                "📥 Download Schedule",
                schedule,
                file_name="study_schedule.txt",
                mime="text/plain"
            )
        else:
            st.error("Please enter your subjects!")

elif menu == "👨‍🏫 Teacher Mode":
    st.header("👨‍🏫 Teacher Mode - Get Tested!")
    st.info("📝 Take tests and get graded! No answers shown until you submit.")
    
    # Initialize test state
    if "test_active" not in st.session_state:
        st.session_state.test_active = False
    if "test_questions" not in st.session_state:
        st.session_state.test_questions = []
    if "test_answers" not in st.session_state:
        st.session_state.test_answers = {}
    if "test_submitted" not in st.session_state:
        st.session_state.test_submitted = False
    if "test_score" not in st.session_state:
        st.session_state.test_score = None
    
    # Test Setup (if no active test)
    if not st.session_state.test_active:
        st.write("### 📚 Create Your Test")
        
        col1, col2 = st.columns(2)
        with col1:
            subject = st.text_input("📖 Subject:", placeholder="e.g., Math, History, Biology")
        with col2:
            topic = st.text_input("📌 Topic:", placeholder="e.g., Algebra, World War 2")
        
        col3, col4 = st.columns(2)
        with col3:
            difficulty = st.selectbox("🎯 Difficulty:", ["Easy", "Medium", "Hard", "Expert"])
        with col4:
            num_questions = st.slider("❓ Questions:", 3, 10, 5)
        
        if st.button("🎯 Generate Test", use_container_width=True, type="primary"):
            if subject:
                prompt = f"""Create a {num_questions}-question multiple choice test about {subject} - {topic} ({difficulty} level).

Format EXACTLY like this:

QUESTION 1
What is the capital of France?
A) London
B) Paris
C) Berlin
D) Madrid
CORRECT_ANSWER: B

QUESTION 2
[Next question]
A) [option]
B) [option]
C) [option]
D) [option]
CORRECT_ANSWER: [letter]

Continue for all {num_questions} questions.
Make them challenging and educational!"""
                
                with st.spinner("👨‍🏫 Teacher is preparing your test..."):
                    test_content = ask_ai(prompt, include_memory=False)
                
                # Parse the test
                try:
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
                            option_letter = line[0]
                            option_text = line[2:].strip()
                            current_q['options'][option_letter] = option_text
                        elif 'CORRECT_ANSWER' in line:
                            answer = line.split(':')[1].strip()
                            current_q['correct'] = answer
                    
                    # Add last question
                    if current_q and 'question' in current_q:
                        questions.append(current_q)
                    
                    if questions:
                        st.session_state.test_questions = questions
                        st.session_state.test_active = True
                        st.session_state.test_answers = {}
                        st.session_state.test_submitted = False
                        st.success("✅ Test generated! Good luck!")
                        st.rerun()
                    else:
                        st.error("Failed to generate test. Try again!")
                except Exception as e:
                    st.error(f"Error parsing test: {e}")
            else:
                st.error("Please enter a subject!")
    
    # Display Active Test
    elif st.session_state.test_active and not st.session_state.test_submitted:
        st.write("### 📝 Your Test")
        st.warning("⚠️ Choose your answers carefully! You can only submit once.")
        
        progress = len(st.session_state.test_answers) / len(st.session_state.test_questions)
        st.progress(progress)
        st.caption(f"Answered: {len(st.session_state.test_answers)}/{len(st.session_state.test_questions)}")
        
        st.markdown("---")
        
        # Display all questions
        for idx, q in enumerate(st.session_state.test_questions):
            st.write(f"**Question {q['number']}**")
            st.write(q['question'])
            
            # Radio buttons for answers
            answer = st.radio(
                "Select your answer:",
                options=list(q['options'].keys()),
                format_func=lambda x: f"{x}) {q['options'][x]}",
                key=f"q_{idx}",
                index=None
            )
            
            if answer:
                st.session_state.test_answers[idx] = answer
            
            st.markdown("---")
        
        # Submit button
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📤 Submit Test", use_container_width=True, type="primary"):
                if len(st.session_state.test_answers) < len(st.session_state.test_questions):
                    st.error(f"⚠️ Please answer all questions! ({len(st.session_state.test_answers)}/{len(st.session_state.test_questions)} answered)")
                else:
                    st.session_state.test_submitted = True
                    st.rerun()
    
    # Show Results
    elif st.session_state.test_submitted:
        st.write("### 📊 Test Results")
        
        # Calculate score
        correct = 0
        total = len(st.session_state.test_questions)
        
        for idx, q in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.test_answers.get(idx)
            correct_answer = q.get('correct')
            
            if user_answer == correct_answer:
                correct += 1
        
        score_percentage = (correct / total) * 100
        
        # Display score with styling
        st.markdown("---")
        
        if score_percentage >= 90:
            st.success(f"🌟 **EXCELLENT!** {correct}/{total} ({score_percentage:.0f}%)")
            st.balloons()
        elif score_percentage >= 70:
            st.info(f"✅ **GOOD JOB!** {correct}/{total} ({score_percentage:.0f}%)")
        elif score_percentage >= 50:
            st.warning(f"📚 **KEEP PRACTICING!** {correct}/{total} ({score_percentage:.0f}%)")
        else:
            st.error(f"💪 **STUDY MORE!** {correct}/{total} ({score_percentage:.0f}%)")
        
        st.markdown("---")
        
        # Detailed breakdown
        st.write("### 📋 Detailed Breakdown")
        
        for idx, q in enumerate(st.session_state.test_questions):
            user_answer = st.session_state.test_answers.get(idx)
            correct_answer = q.get('correct')
            is_correct = user_answer == correct_answer
            
            # Question header with icon
            if is_correct:
                st.success(f"✅ Question {q['number']}")
            else:
                st.error(f"❌ Question {q['number']}")
            
            # Show question
            st.write(f"**{q['question']}**")
            
            # Show all options with highlighting
            for letter, text in q['options'].items():
                if letter == correct_answer and letter == user_answer:
                    st.success(f"✅ {letter}) {text} ← Your answer (CORRECT!)")
                elif letter == correct_answer:
                    st.info(f"✓ {letter}) {text} ← Correct answer")
                elif letter == user_answer:
                    st.error(f"✗ {letter}) {text} ← Your answer (Wrong)")
                else:
                    st.write(f"  {letter}) {text}")
            
            st.markdown("---")
        
        # Award XP based on score
        xp_earned = int(correct * 10)  # 10 XP per correct answer
        
        try:
            current_xp = user_data.get('xp', 0)
            supabase.table("profiles").update({
                "xp": current_xp + xp_earned
            }).eq("id", st.session_state.user.id).execute()
            
            st.success(f"⭐ You earned {xp_earned} XP!")
        except:
            pass
        
        # New test button
        if st.button("🔄 Take Another Test", use_container_width=True, type="primary"):
            st.session_state.test_active = False
            st.session_state.test_questions = []
            st.session_state.test_answers = {}
            st.session_state.test_submitted = False
            st.session_state.test_score = None
            st.rerun()

elif menu == "📸 Image Analysis":
    st.header("📸 Image Analysis Lab")
    st.caption("🔍 Real AI-powered image analysis using Groq Vision!")

    def analyze_image_with_groq(image_file, prompt):
        """Direct image analysis using Groq vision model"""
        try:
            import base64

            # Convert image to base64
            img = Image.open(image_file)

            # Convert to RGB if needed (removes alpha channel)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Save to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            buffer.seek(0)
            image_bytes = buffer.read()

            # Encode to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")

            # Call Groq vision model
            response = groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",  # Groq vision model
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

        except Exception as e:
            error_str = str(e)
            if "model" in error_str.lower() or "not found" in error_str.lower():
                # Try fallback vision model
                try:
                    response = groq_client.chat.completions.create(
                        model="llava-v1.5-7b-4096-preview",
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
                except Exception as e2:
                    return None, str(e2)
            return None, error_str

    # Tabs for upload vs camera
    tab1, tab2 = st.tabs(["📤 Upload Image", "📷 Take Photo"])

    with tab1:
        uploaded_file = st.file_uploader(
            "Upload your study material",
            type=['png', 'jpg', 'jpeg', 'webp'],
            key="img_upload"
        )

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Your Image", width=450)

            st.markdown("---")

            # Analysis type
            analysis_type = st.radio(
                "📋 What do you want to know?",
                [
                    "📝 Explain everything in this image",
                    "💡 Summarize the key points",
                    "❓ Generate practice questions",
                    "🔍 Identify formulas and concepts",
                    "📊 Explain diagrams or charts",
                    "✍️ Custom question"
                ],
                key="analysis_type_upload"
            )

            custom_q = ""
            if analysis_type == "✍️ Custom question":
                custom_q = st.text_input("Type your question about the image:", key="custom_q")

            prompt_map = {
                "📝 Explain everything in this image": "You are an expert study assistant. Explain everything you see in this image in detail. If it's a textbook page, explain the content. If it's a diagram, explain what it shows. Be thorough and educational.",
                "💡 Summarize the key points": "You are an expert study assistant. Look at this image and summarize all the key points and important information. Format as a numbered list.",
                "❓ Generate practice questions": "You are an expert study assistant. Based on what you see in this image, create 5 practice exam questions with answers. Make them educational and relevant to the content shown.",
                "🔍 Identify formulas and concepts": "You are an expert study assistant. Identify and explain every formula, equation, concept, or technical term visible in this image. Give a clear explanation of each one.",
                "📊 Explain diagrams or charts": "You are an expert study assistant. Describe and explain this diagram or chart in detail. What does it show? What are the key takeaways? What does each part mean?",
                "✍️ Custom question": custom_q if custom_q else "Describe what you see in this image."
            }

            if st.button("🔍 Analyze Image", use_container_width=True, type="primary", key="analyze_upload"):
                if analysis_type == "✍️ Custom question" and not custom_q:
                    st.error("Please type your question first!")
                else:
                    prompt = prompt_map[analysis_type]

                    with st.spinner("🧠 Groq Vision is analyzing your image..."):
                        result, error = analyze_image_with_groq(uploaded_file, prompt)

                    if result:
                        st.markdown("---")
                        st.write("### 📋 Analysis Result:")
                        st.markdown(result)
                        st.markdown("---")

                        # Download button
                        st.download_button(
                            "📥 Download Analysis",
                            result,
                            file_name="image_analysis.txt",
                            mime="text/plain"
                        )

                        # Award XP
                        try:
                            current_xp = user_data.get('xp', 0)
                            supabase.table("profiles").update({
                                "xp": current_xp + 10
                            }).eq("id", st.session_state.user.id).execute()
                            st.caption("⭐ +10 XP earned!")
                        except:
                            pass
                    else:
                        st.error(f"❌ Analysis failed: {error}")
                        st.info("💡 Make sure your image is clear and not too large!")

    with tab2:
        st.write("📷 Take a photo of your study material!")
        camera_photo = st.camera_input("Point camera at your notes or textbook", key="camera_input")

        if camera_photo:
            st.success("📸 Photo captured!")

            analysis_type_cam = st.radio(
                "📋 What do you want to know?",
                [
                    "📝 Explain everything",
                    "💡 Key points only",
                    "❓ Practice questions",
                    "✍️ Custom question"
                ],
                key="analysis_type_cam"
            )

            custom_q_cam = ""
            if analysis_type_cam == "✍️ Custom question":
                custom_q_cam = st.text_input("Your question:", key="custom_q_cam")

            prompt_map_cam = {
                "📝 Explain everything": "You are an expert study assistant. Explain everything you see in this image in detail. Be thorough and educational.",
                "💡 Key points only": "You are an expert study assistant. List only the key points visible in this image as a numbered list.",
                "❓ Practice questions": "You are an expert study assistant. Create 5 practice questions based on what you see in this image.",
                "✍️ Custom question": custom_q_cam if custom_q_cam else "Describe this image."
            }

            if st.button("🔍 Analyze Photo", use_container_width=True, type="primary", key="analyze_cam"):
                if analysis_type_cam == "✍️ Custom question" and not custom_q_cam:
                    st.error("Please type your question!")
                else:
                    prompt = prompt_map_cam[analysis_type_cam]

                    with st.spinner("🧠 Groq Vision is analyzing your photo..."):
                        result, error = analyze_image_with_groq(camera_photo, prompt)

                    if result:
                        st.markdown("---")
                        st.write("### 📋 Analysis Result:")
                        st.markdown(result)
                        st.markdown("---")

                        st.download_button(
                            "📥 Download Analysis",
                            result,
                            file_name="photo_analysis.txt",
                            mime="text/plain"
                        )

                        # Award XP
                        try:
                            current_xp = user_data.get('xp', 0)
                            supabase.table("profiles").update({
                                "xp": current_xp + 10
                            }).eq("id", st.session_state.user.id).execute()
                            st.caption("⭐ +10 XP earned!")
                        except:
                            pass
                    else:
                        st.error(f"❌ Analysis failed: {error}")
                        st.info("💡 Try taking a clearer photo with good lighting!")
                
elif menu == "🗂️ Flashcards":
    st.header("🗂️ Flashcard Generator")
    st.write("Create study flashcards instantly!")
    
    topic = st.text_input("📚 Topic:", placeholder="e.g., Spanish Vocabulary, Biology Terms")
    num_cards = st.slider("🎴 Number of flashcards:", 5, 20, 10)
    
    if st.button("🎴 Generate Flashcards", use_container_width=True, type="primary"):
        if topic:
            prompt = f"""Create {num_cards} flashcards for studying {topic}.

Format each flashcard like this:

**Card 1**
Front: [Question or term]
Back: [Answer or definition]

**Card 2**
Front: [Question or term]
Back: [Answer or definition]

etc.

Make them clear, concise, and educational!"""
            
            with st.spinner("🎨 Creating flashcards..."):
                flashcards = ask_ai(prompt, include_memory=False)
            
            st.markdown("---")
            st.markdown(flashcards)
            st.markdown("---")
            
            st.download_button(
                "📥 Download Flashcards",
                flashcards,
                file_name=f"flashcards_{topic.replace(' ', '_')}.txt",
                mime="text/plain"
            )
        else:
            st.error("Please enter a topic!")

elif menu == "📊 Dashboard":
    st.header("📊 Your Study Dashboard")
    
    try:
        # User stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("👤 Username", user_data.get('username', 'User'))
        
        with col2:
            st.metric("📊 Level", level)
        
        with col3:
            xp = user_data.get('xp', 0)
            st.metric("⭐ XP Points", xp)
        
        # Premium status
        if user_data.get('is_premium'):
            st.success("💎 Premium Member")
        else:
            st.info("⭐ Free Account - Upgrade to Premium for unlimited access!")
        
        st.markdown("---")
        
        # Activity stats
        st.subheader("📈 Recent Activity")
        
        try:
            # Count messages
            hist_count = supabase.table("history").select("id", count="exact").eq(
                "user_id", st.session_state.user.id
            ).execute()
            
            total_chats = hist_count.count if hist_count.count else 0
            
            # Count schedules
            sched_count = supabase.table("schedules").select("id", count="exact").eq(
                "user_id", st.session_state.user.id
            ).execute()
            
            total_schedules = sched_count.count if sched_count.count else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("💬 Total Chats", total_chats)
            with col2:
                st.metric("📅 Schedules Created", total_schedules)
            
        except:
            st.info("No activity data yet!")
        
        st.markdown("---")
        
        # Recent conversations
        st.subheader("📜 Recent Conversations")
        
        try:
            recent = supabase.table("history").select("*").eq(
                "user_id", st.session_state.user.id
            ).order("created_at", desc=True).limit(10).execute()
            
            if recent.data:
                for msg in recent.data:
                    role_icon = "👤" if msg.get("role") == "user" else "🤖"
                    content = msg.get("content", "")
                    timestamp = msg.get("created_at", "")[:19]
                    
                    with st.expander(f"{role_icon} {content[:50]}..." if len(content) > 50 else f"{role_icon} {content}"):
                        st.write(content)
                        st.caption(f"🕒 {timestamp}")
            else:
                st.info("No conversations yet. Start chatting!")
        except:
            st.info("Chat history unavailable")
        
    except Exception as e:
        st.error(f"Dashboard error: {e}")
