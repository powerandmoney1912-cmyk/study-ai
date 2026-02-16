import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time
import base64
from PIL import Image
import io

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Study Master Infinity", layout="wide", page_icon="🎓")

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
    st.title("🛡️ Study Master Infinity")
    st.subheader("⚡ Powered by Groq - Ultra Fast AI")
    
    t1, t2 = st.tabs(["🔑 Login", "✨ Sign Up"])
    
    with t1:
        e = st.text_input("Email", key="login_email")
        p = st.text_input("Password", type="password", key="login_pass")
        if st.button("🚀 Log In", use_container_width=True, type="primary"):
            if e and p:
                try:
                    res = supabase.auth.sign_in_with_password({"email": e, "password": p})
                    st.session_state.user = res.user
                    st.success("✅ Login successful!")
                    time.sleep(0.5)
                    st.rerun()
                except Exception as err:
                    st.error(f"❌ Login failed: {err}")
            else:
                st.error("Enter email and password")
    
    with t2:
        ne = st.text_input("Email", key="signup_email")
        np = st.text_input("Password (min 6 chars)", type="password", key="signup_pass")
        confirm_p = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("🎉 Create Account", use_container_width=True, type="primary"):
            if ne and np and confirm_p:
                if np != confirm_p:
                    st.error("❌ Passwords don't match!")
                elif len(np) < 6:
                    st.error("❌ Password too short!")
                else:
                    try:
                        supabase.auth.sign_up({"email": ne, "password": np})
                        st.success("✅ Account created! Check email to verify.")
                        st.balloons()
                    except Exception as err:
                        st.error(f"❌ Error: {err}")
            else:
                st.error("Fill all fields")
    st.stop()

# Check/Create Profile
try:
    profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
    
    if not profile_res.data:
        st.title("👋 Welcome! Set Up Your Profile")
        u_name = st.text_input("Choose a Username", placeholder="e.g., StudyNinja")
        if st.button("💾 Save Profile", type="primary"):
            if u_name:
                supabase.table("profiles").insert({
                    "id": st.session_state.user.id,
                    "username": u_name,
                    "xp": 0,
                    "is_premium": False,
                    "created_at": datetime.now().isoformat()
                }).execute()
                st.success("Profile created!")
                st.rerun()
            else:
                st.error("Enter a username")
        st.stop()
    
    user_data = profile_res.data[0]
except Exception as e:
    st.error(f"Profile error: {e}")
    user_data = {"username": "User", "xp": 0, "is_premium": False}

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title(f"👤 {user_data.get('username', 'User')}")
    level = user_data.get('xp', 0) // 100 + 1
    st.write(f"📊 Level: {level}")
    st.progress(min((user_data.get('xp', 0) % 100) / 100, 1.0))
    
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
    st.write("Upload or capture images of your study materials!")
    
    tab1, tab2 = st.tabs(["📤 Upload Image", "📷 Take Photo"])
    
    with tab1:
        uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", width=400)
            
            analysis_type = st.radio("What would you like to know?", [
                "📝 Explain the content",
                "💡 Summarize key points",
                "❓ Generate practice questions",
                "🔍 Identify formulas/concepts"
            ])
            
            if st.button("🔍 Analyze Image", type="primary"):
                prompt_map = {
                    "📝 Explain the content": "Explain what's shown in this study material in detail.",
                    "💡 Summarize key points": "List the key points and concepts from this image.",
                    "❓ Generate practice questions": "Create 5 practice questions based on the content in this image.",
                    "🔍 Identify formulas/concepts": "Identify and explain any formulas, equations, or key concepts shown."
                }
                
                # Note: Groq doesn't support image input yet
                st.warning("⚠️ Image recognition coming soon!")
                st.info("💡 **Workaround:** Describe what you see in the image, and I'll help you understand it!")
                
                image_desc = st.text_area("Describe what you see in the image:", 
                                         placeholder="e.g., A diagram showing the water cycle with labels...")
                
                if image_desc:
                    prompt = f"{prompt_map[analysis_type]}\n\nImage description: {image_desc}"
                    
                    with st.spinner("Analyzing..."):
                        result = ask_ai(prompt, include_memory=False)
                    
                    st.markdown("---")
                    st.markdown(result)
    
    with tab2:
        camera_photo = st.camera_input("Take a picture")
        
        if camera_photo:
            st.success("📸 Photo captured!")
            st.info("💡 **Coming Soon:** Direct image analysis!")
            st.write("For now, please describe what's in the photo:")
            
            photo_desc = st.text_area("What's in the photo?", 
                                     placeholder="Describe the content...")
            
            if photo_desc and st.button("Analyze", type="primary"):
                prompt = f"Help me understand this study material: {photo_desc}"
                
                with st.spinner("Analyzing..."):
                    result = ask_ai(prompt, include_memory=False)
                
                st.markdown("---")
                st.markdown(result)

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
