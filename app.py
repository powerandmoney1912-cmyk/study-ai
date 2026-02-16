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
        "👨‍🏫 Tutor Mode",
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

elif menu == "👨‍🏫 Tutor Mode":
    st.header("👨‍🏫 Socratic Tutor")
    st.info("💡 Learn through guided questions - the tutor won't give you direct answers!")
    
    problem = st.text_area("📝 What problem are you trying to solve?", 
                          height=150,
                          placeholder="Describe what you're stuck on...")
    
    if st.button("🚀 Start Tutoring", use_container_width=True, type="primary"):
        if problem:
            prompt = f"""Act as a Socratic tutor helping a student with this problem:
"{problem}"

Your role:
- Ask 3-4 guiding questions that help them discover the answer
- DO NOT give the direct answer
- Help them think critically
- Be encouraging and supportive
- Build on their responses

Start with: "Let me help you think through this step by step..."
"""
            
            with st.spinner("🤔 Preparing questions..."):
                response = ask_ai(prompt, include_memory=False)
            
            st.markdown("---")
            st.markdown(response)
            st.markdown("---")
            
            st.info("💬 Continue the conversation in the Chat tab for back-and-forth learning!")
        else:
            st.error("Please describe your problem!")

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
