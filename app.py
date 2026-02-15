# Supabase version - Updated Feb 2025
import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PyPDF2
from PIL import Image
import json

# Page Configuration
st.set_page_config(page_title="AI Study Assistant", page_icon="🎓", layout="wide")

# Initialize Supabase
@st.cache_resource
def init_supabase():
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Supabase initialization error: {str(e)}")
        st.info("Please check your Supabase credentials in secrets")
        st.stop()

supabase: Client = init_supabase()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# PREMIUM CODES WITH EXPIRY
PREMIUM_CODES = {
    "PREMIUM2024": {"description": "Valid until Dec 2024", "days": 365},
    "STUDENT100": {"description": "Student Special Access", "days": 365},
    "TEACHER50": {"description": "Teacher Premium", "days": 365},
    "LIFETIME": {"description": "Lifetime Premium Access", "days": 36500},
    "Aarya": {"description": "1 Day Premium", "days": 1},
    "Manu Aarya": {"description": "27 Days Premium", "days": 27}
}

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'study_mode' not in st.session_state:
    st.session_state.study_mode = "AI Chat"
if 'is_premium' not in st.session_state:
    st.session_state.is_premium = False
if 'premium_expires' not in st.session_state:
    st.session_state.premium_expires = None

# NCERT Configuration
NCERT_SUBJECTS = {
    "Mathematics": ["Algebra", "Geometry", "Trigonometry", "Calculus", "Statistics", "Probability"],
    "Science": ["Physics", "Chemistry", "Biology", "Environmental Science"],
    "Social Science": ["History", "Geography", "Political Science", "Economics"],
    "English": ["Grammar", "Literature", "Writing", "Comprehension"],
    "Tamil": ["Grammar", "Literature", "Poetry", "Prose"],
    "Hindi": ["Grammar", "Literature", "Poetry", "Prose"],
    "Marathi": ["Grammar", "Literature", "Poetry", "Prose"]
}
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard", "Expert"]
NCERT_CLASSES = ["Class 6", "Class 7", "Class 8", "Class 9", "Class 10", "Class 11", "Class 12"]

# Custom CSS
st.markdown("""<style>
    .stButton>button {width: 100%; background-color: #4CAF50; color: white; font-weight: bold;}
    .premium-badge {
        background: linear-gradient(45deg, #FFD700, #FFA500);
        color: #000;
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin: 10px 0;
    }
    .chat-message {padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem;}
    .user-message {background-color: #e3f2fd; border-left: 5px solid #2196F3;}
    .ai-message {background-color: #f1f8e9; border-left: 5px solid #4CAF50;}
</style>""", unsafe_allow_html=True)

# Authentication Functions
def create_account(email, password, name):
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name
                }
            }
        })
        
        if auth_response.user:
            supabase.table('users').insert({
                'id': auth_response.user.id,
                'name': name,
                'email': email,
                'created_at': datetime.now().isoformat(),
                'total_questions': 0,
                'is_premium': False,
                'premium_activated_at': None,
                'premium_expires_at': None
            }).execute()
            
            return True, "Account created successfully! Please check your email to verify."
        else:
            return False, "Account creation failed"
            
    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg or "already registered" in error_msg:
            return False, "This email is already registered!"
        elif "Invalid email" in error_msg:
            return False, "Invalid email address!"
        elif "Password should be" in error_msg or "weak" in error_msg.lower():
            return False, "Password is too weak. Use at least 6 characters!"
        return False, f"Error: {error_msg}"

def login_user(email, password):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user:
            user_id = auth_response.user.id
            user_data = supabase.table('users').select('*').eq('id', user_id).execute()
            
            if user_data.data and len(user_data.data) > 0:
                user_info = user_data.data[0]
                is_premium = user_info.get('is_premium', False)
                premium_expires = user_info.get('premium_expires_at')
                
                # Check if premium expired
                if is_premium and premium_expires:
                    expiry_date = datetime.fromisoformat(premium_expires)
                    if datetime.now() > expiry_date:
                        # Premium expired, update database
                        supabase.table('users').update({
                            'is_premium': False
                        }).eq('id', user_id).execute()
                        is_premium = False
                        premium_expires = None
                
                st.session_state.user = {
                    'uid': user_id,
                    'email': auth_response.user.email,
                    'name': user_info.get('name', 'User')
                }
                st.session_state.is_premium = is_premium
                st.session_state.premium_expires = premium_expires
                return True, "Login successful!"
            else:
                return False, "User profile not found"
        else:
            return False, "Login failed"
            
    except Exception as e:
        error_msg = str(e)
        if "Invalid login credentials" in error_msg:
            return False, "Invalid email or password!"
        return False, f"Login error: {error_msg}"

def activate_premium(code):
    """Activate premium with code"""
    if code in PREMIUM_CODES:
        try:
            code_info = PREMIUM_CODES[code]
            expiry_date = datetime.now() + timedelta(days=code_info['days'])
            
            supabase.table('users').update({
                'is_premium': True,
                'premium_activated_at': datetime.now().isoformat(),
                'premium_expires_at': expiry_date.isoformat(),
                'premium_code_used': code
            }).eq('id', st.session_state.user['uid']).execute()
            
            st.session_state.is_premium = True
            st.session_state.premium_expires = expiry_date.isoformat()
            
            return True, f"✅ Premium Activated! {code_info['description']} - Expires: {expiry_date.strftime('%Y-%m-%d')}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    else:
        return False, "❌ Invalid premium code!"

# AI Functions
def get_ai_response(prompt, mode="chat"):
    try:
        if st.session_state.is_premium:
            model = genai.GenerativeModel('gemini-1.5-flash')
            model_name = "⚡ Gemini 1.5 Flash"
        else:
            model = genai.GenerativeModel('gemini-pro')
            model_name = "Gemini Pro"
        
        prompts = {
            "chat": "You are an NCERT-aligned AI tutor. Provide clear, detailed educational responses.",
            "socratic": "You are a Socratic tutor. Ask guiding questions, never give direct answers. Follow NCERT curriculum.",
            "simplify": "Explain like I'm 5 years old. Use simple words, fun examples. Follow NCERT curriculum.",
        }
        full_prompt = f"{prompts.get(mode, prompts['chat'])}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        
        footer = f"\n\n*Powered by {model_name}*" if st.session_state.is_premium else ""
        return response.text + footer
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}\n\nPlease try again or check your API key."

def analyze_image(image_file, prompt="Explain this image"):
    try:
        if st.session_state.is_premium:
            model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            model = genai.GenerativeModel('gemini-pro-vision')
        
        image = Image.open(image_file)
        response = model.generate_content([prompt + " Follow NCERT curriculum.", image])
        return response.text
    except Exception as e:
        return f"Image analysis error: {str(e)}"

def summarize_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in pdf_reader.pages])
        
        if st.session_state.is_premium:
            prompt = f"Provide 15 detailed key points:\n\n{text[:12000]}"
        else:
            prompt = f"Summarize in 10 key points:\n\n{text[:8000]}"
        
        return get_ai_response(prompt)
    except Exception as e:
        return f"PDF error: {str(e)}"

def generate_quiz(subject, difficulty, class_level, topic=None):
    num_questions = 10 if st.session_state.is_premium else 5
    
    prompt = f"""Generate {num_questions} NCERT {class_level} {subject} MCQs ({difficulty} level).
    {f'Topic: {topic}' if topic else ''}
    Format:
    Q1: [Question]
    A) [Option]
    B) [Option]
    C) [Option]
    D) [Option]
    Correct: [A/B/C/D]
    Explanation: [Brief explanation]"""
    
    response = get_ai_response(prompt)
    questions = []
    lines = response.split('\n')
    current = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith('Q'):
            if current:
                questions.append(current)
            current = {'question': line.split(':', 1)[1].strip() if ':' in line else line, 'options': {}}
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            current['options'][line[0]] = line[2:].strip()
        elif line.startswith('Correct:'):
            current['correct'] = line.split(':')[1].strip()[0]
        elif line.startswith('Explanation:'):
            current['explanation'] = line.split(':', 1)[1].strip()
    
    if current:
        questions.append(current)
    return questions

def save_history(user_id, question, answer):
    try:
        supabase.table('history').insert({
            'user_id': user_id,
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat(),
            'model_used': 'premium' if st.session_state.is_premium else 'free'
        }).execute()
        
        user_data = supabase.table('users').select('total_questions').eq('id', user_id).execute()
        if user_data.data:
            current_count = user_data.data[0].get('total_questions', 0)
            supabase.table('users').update({
                'total_questions': current_count + 1
            }).eq('id', user_id).execute()
    except Exception as e:
        pass

# UI Functions
def show_login():
    st.title("🎓 AI Study Assistant")
    st.caption("NCERT-Aligned Learning Platform")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Welcome Back!")
        email = st.text_input("Email", key="login_email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", key="login_pass", placeholder="••••••")
        
        if st.button("🚀 Login", key="btn_login", use_container_width=True):
            if not email or not password:
                st.warning("Please enter both email and password")
            else:
                with st.spinner("Logging in..."):
                    success, msg = login_user(email, password)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
    with tab2:
        st.subheader("Create Account")
        name = st.text_input("Full Name", key="signup_name", placeholder="Your Name")
        email = st.text_input("Email", key="signup_email", placeholder="your@email.com")
        password = st.text_input("Password", type="password", key="signup_pass", placeholder="Min 6 characters")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm", placeholder="Re-enter password")
        
        if st.button("✨ Create Account", key="btn_signup", use_container_width=True):
            if not name or not email or not password:
                st.warning("Please fill all fields")
            elif password != confirm:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters!")
            else:
                with st.spinner("Creating account..."):
                    success, msg = create_account(email, password, name)
                    if success:
                        st.success(msg)
                        st.info("✅ Account created! Please login above.")
                    else:
                        st.error(msg)

def show_sidebar():
    with st.sidebar:
        if st.session_state.is_premium:
            st.markdown('<div class="premium-badge">👑 PREMIUM USER</div>', unsafe_allow_html=True)
            if st.session_state.premium_expires:
                try:
                    expiry_date = datetime.fromisoformat(st.session_state.premium_expires)
                    days_left = (expiry_date - datetime.now()).days
                    if days_left > 0:
                        st.info(f"⏰ Premium expires in {days_left} days")
                    else:
                        st.warning("⚠️ Premium expired")
                except:
                    pass
        
        st.title(f"👋 {st.session_state.user['name']}")
        
        if not st.session_state.is_premium:
            st.markdown("---")
            with st.expander("🌟 Upgrade to Premium", expanded=False):
                st.write("**Benefits:**")
                st.write("✅ Gemini 1.5 Flash (Faster)")
                st.write("✅ 10 Quiz Questions")
                st.write("✅ Detailed Summaries")
                st.write("")
                st.write("**Available Codes:**")
                st.write("• `Aarya` - 1 Day")
                st.write("• `Manu Aarya` - 27 Days")
                
                premium_code = st.text_input("Premium Code", type="password", key="premium_input")
                if st.button("Activate", key="activate_btn"):
                    success, msg = activate_premium(premium_code)
                    if success:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)
        
        st.markdown("---")
        st.session_state.study_mode = st.selectbox(
            "📚 Study Mode",
            ["AI Chat", "Socratic Tutor", "Quiz Generator", "Simplifier", "Multimedia Tools", "Dashboard"]
        )
        
        st.markdown("---")
        try:
            user_data = supabase.table('users').select('total_questions').eq('id', st.session_state.user['uid']).execute()
            if user_data.data:
                st.metric("Questions", user_data.data[0].get('total_questions', 0))
        except:
            pass
        
        st.caption("🇮🇳 NCERT Aligned")
        
        if st.button("🚪 Logout", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except:
                pass
            st.session_state.user = None
            st.session_state.chat_history = []
            st.session_state.is_premium = False
            st.session_state.premium_expires = None
            st.rerun()

def show_chat(mode="chat"):
    titles = {"chat": "💬 AI Chat", "socratic": "🤔 Socratic Tutor", "simplify": "🧒 Simplifier"}
    st.title(titles.get(mode, "💬 Chat"))
    
    if st.session_state.is_premium:
        st.success("⚡ Using Gemini 1.5 Flash!")
    
    for msg in st.session_state.chat_history:
        css = "user-message" if msg['role'] == 'user' else "ai-message"
        st.markdown(f'<div class="chat-message {css}"><b>{msg["role"].title()}:</b> {msg["content"]}</div>', 
                   unsafe_allow_html=True)
    
    user_input = st.chat_input("Ask anything...")
    if user_input:
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        with st.spinner("Thinking..."):
            response = get_ai_response(user_input, mode)
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            save_history(st.session_state.user['uid'], user_input, response)
        st.rerun()
    
    if len(st.session_state.chat_history) > 0:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

def show_quiz():
    st.title("📝 NCERT Quiz Generator")
    
    if st.session_state.is_premium:
        st.success("👑 Premium: 10 questions per quiz!")
    else:
        st.info("Free: 5 questions. Upgrade for 10!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox("Subject", list(NCERT_SUBJECTS.keys()))
    with col2:
        class_level = st.selectbox("Class", NCERT_CLASSES)
    with col3:
        difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
    
    topic = st.selectbox("Topic", ["All Topics"] + NCERT_SUBJECTS[subject])
    
    if st.button("🎯 Generate Quiz"):
        with st.spinner("Creating questions..."):
            st.session_state.quiz_data = generate_quiz(
                subject, difficulty, class_level, 
                None if topic == "All Topics" else topic
            )
            st.session_state.quiz_answers = {}
    
    if 'quiz_data' in st.session_state and st.session_state.quiz_data:
        st.markdown("---")
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Q{idx+1}:** {q['question']}")
            answer = st.radio("", list(q['options'].keys()), 
                            format_func=lambda x: f"{x}) {q['options'][x]}", key=f"q_{idx}")
            st.session_state.quiz_answers[idx] = answer
            st.markdown("---")
        
        if st.button("✅ Submit"):
            score = sum(1 for idx, q in enumerate(st.session_state.quiz_data) 
                       if st.session_state.quiz_answers.get(idx) == q['correct'])
            percentage = (score / len(st.session_state.quiz_data)) * 100
            
            for idx, q in enumerate(st.session_state.quiz_data):
                is_correct = st.session_state.quiz_answers.get(idx) == q['correct']
                if is_correct:
                    st.success(f"✅ Q{idx+1}: Correct!")
                else:
                    st.error(f"❌ Q{idx+1}: Wrong - Answer: {q['correct']}) {q['options'][q['correct']]}")
                if 'explanation' in q:
                    st.caption(f"💡 {q['explanation']}")
            
            st.markdown(f"## Score: {score}/{len(st.session_state.quiz_data)} ({percentage:.0f}%)")
            if percentage >= 80:
                st.balloons()

def show_multimedia():
    st.title("🎨 Multimedia Tools")
    
    tab1, tab2 = st.tabs(["📷 Image", "📄 PDF"])
    
    with tab1:
        uploaded_img = st.file_uploader("Upload image", type=['png', 'jpg', 'jpeg'])
        if uploaded_img:
            st.image(uploaded_img, width=400)
            if st.button("Analyze"):
