import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image
import os

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

# --- 6. LOGIN SCREEN ---
def login_screen():
    st.title("🎓 Study Master Pro")
    st.subheader("Your AI-Powered Study Companion")
    
    if not supabase:
        st.error("Supabase connection failed.")
        return
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="l_email")
        password = st.text_input("Password", type="password", key="l_pass")
        
        if st.button("Log In", use_container_width=True):
            if email and password:
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
            else:
                st.error("Enter email and password")
    
    with tab2:
        new_email = st.text_input("Email", key="s_email")
        new_pass = st.text_input("Password (6+ chars)", type="password", key="s_pass")
        confirm_pass = st.text_input("Confirm Password", type="password", key="s_confirm")
        
        if st.button("Create Account", use_container_width=True):
            if not new_email or not new_pass:
                st.error("Fill all fields")
            elif len(new_pass) < 6:
                st.error("Password too short")
            elif new_pass != confirm_pass:
                st.error("Passwords don't match")
            else:
                try:
                    supabase.auth.sign_up({"email": new_email, "password": new_pass})
                    st.success("Account created! Check email to verify.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

# --- 7. MAIN APP ---
if st.session_state.user:
    if not model:
        st.error("⚠️ AI unavailable. Check errors above.")
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.rerun()
        st.stop()
    
    # Sidebar
    st.sidebar.title("💎 Study Master")
    
    # Premium
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 Premium Code"):
            code = st.text_input("Code", type="password", key="prem")
            if st.button("Activate", key="activate_premium"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
                else:
                    st.error("Invalid")
    else:
        st.sidebar.success("✨ Premium Active")
    
    # Usage
    usage = get_daily_usage()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{usage}/{limit}")
    st.sidebar.progress(min(usage/limit, 1.0))
    
    menu = st.sidebar.radio("Menu", ["Chat", "Quiz", "Image", "Tutor"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
    
    # Features
    if usage >= limit:
        st.error(f"⚠️ Daily limit reached ({usage}/{limit})")
        st.info("Upgrade to Premium or wait 24 hours")
    else:
        if menu == "Chat":
            st.subheader("💬 AI Study Chat")
            q = st.chat_input("Ask anything...")
            if q:
                with st.chat_message("user"):
                    st.write(q)
                try:
                    with st.spinner("Thinking..."):
                        resp = model.generate_content(q)
                    with st.chat_message("assistant"):
                        st.write(resp.text)
                    if supabase:
                        supabase.table("history").insert({
                            "user_id": st.session_state.user.id,
                            "question": q,
                            "answer": resp.text
                        }).execute()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        elif menu == "Quiz":
            st.subheader("📝 Quiz Generator")
            
            # Input fields
            topic = st.text_input("Enter topic (e.g., Biology, History):", key="quiz_topic")
            difficulty = st.selectbox("Difficulty Level:", ["Easy", "Medium", "Hard"], key="quiz_diff")
            num_questions = st.slider("Number of Questions:", 3, 10, 5, key="quiz_num")
            
            # Generate button - FIXED with unique key
            if st.button("🎯 Generate Quiz", use_container_width=True, key="generate_quiz_btn"):
                if not topic:
                    st.error("Please enter a topic!")
                else:
                    try:
                        with st.spinner("Creating your quiz..."):
                            prompt = f"""Create a {num_questions}-question multiple choice quiz about {topic} at {difficulty} difficulty level.

Format each question like this:
**Question 1:** [question text]
A) [option]
B) [option]
C) [option]
D) [option]

After all questions, provide:
**Answer Key:**
1. [correct answer]
2. [correct answer]
etc.
"""
                            resp = model.generate_content(prompt)
                            
                        st.markdown("---")
                        st.markdown(resp.text)
                        st.markdown("---")
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Quiz",
                            data=resp.text,
                            file_name=f"quiz_{topic.replace(' ', '_')}.txt",
                            mime="text/plain",
                            key="download_quiz"
                        )
                        
                        # Save to history
                        if supabase:
                            supabase.table("history").insert({
                                "user_id": st.session_state.user.id,
                                "question": f"Quiz: {topic} ({difficulty})",
                                "answer": resp.text
                            }).execute()
                            
                    except Exception as e:
                        st.error(f"Error generating quiz: {e}")
        
        elif menu == "Image":
            st.subheader("📁 Image Analysis")
            st.write("Upload study materials like diagrams, notes, or textbook pages")
            
            file = st.file_uploader("Upload image:", type=['jpg', 'png', 'jpeg'], key="image_upload")
            
            if file:
                try:
                    img = PIL.Image.open(file)
                    st.image(img, caption="Your upload", use_container_width=True)
                    
                    # Analysis button - FIXED
                    if st.button("🔍 Analyze Image", use_container_width=True, key="analyze_img_btn"):
                        with st.spinner("Analyzing image..."):
                            resp = model.generate_content([
                                """Analyze this study material and provide:
1. **Summary** - What is this about?
2. **Key Concepts** - Main ideas and topics
3. **Important Details** - Facts, formulas, dates
4. **Study Tips** - How to remember this material
5. **Practice Questions** - 2-3 questions to test understanding""",
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
        
        elif menu == "Tutor":
            st.subheader("🎯 Socratic Tutor")
            st.info("💡 The Socratic method helps you learn by asking guiding questions instead of giving direct answers.")
            
            problem = st.text_area("Describe your problem or question:", height=150, key="tutor_problem")
            
            # Start button - FIXED
            if st.button("🚀 Start Tutoring Session", use_container_width=True, key="start_tutor_btn"):
                if not problem:
                    st.error("Please describe your problem first!")
                else:
                    try:
                        with st.spinner("Preparing guiding questions..."):
                            resp = model.generate_content(f"""Act as a Socratic tutor. For this student problem:

"{problem}"

Do NOT give the direct answer. Instead:
1. Ask 3-4 guiding questions that help the student think through the problem
2. Each question should lead them closer to discovering the answer themselves
3. Use the Socratic method to develop critical thinking
4. Be encouraging and supportive

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

else:
    login_screen()
