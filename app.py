# Supabase version - Updated Feb 2026 - FIXED FULL VERSION
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
        # Standard keys used by Supabase setup
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Supabase initialization error: {str(e)}")
        st.info("Please check your secrets.toml file")
        st.stop()

supabase: Client = init_supabase()
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

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
            "options": {"data": {"name": name}}
        })
        if auth_response.user:
            supabase.table('users').insert({
                'id': auth_response.user.id,
                'name': name,
                'email': email,
                'total_questions': 0,
                'is_premium': False
            }).execute()
            return True, "Account created! Please login."
        return False, "Creation failed."
    except Exception as e:
        return False, str(e)

def login_user(email, password):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if auth_response.user:
            user_data = supabase.table('users').select('*').eq('id', auth_response.user.id).execute()
            if user_data.data:
                user_info = user_data.data[0]
                st.session_state.user = {'uid': auth_response.user.id, 'email': email, 'name': user_info.get('name')}
                st.session_state.is_premium = user_info.get('is_premium', False)
                st.session_state.premium_expires = user_info.get('premium_expires_at')
                return True, "Login success!"
        return False, "Login failed."
    except Exception as e:
        return False, str(e)

def activate_premium(code):
    if code in PREMIUM_CODES:
        expiry_date = datetime.now() + timedelta(days=PREMIUM_CODES[code]['days'])
        supabase.table('users').update({
            'is_premium': True,
            'premium_expires_at': expiry_date.isoformat()
        }).eq('id', st.session_state.user['uid']).execute()
        st.session_state.is_premium = True
        return True, "Premium Activated!"
    return False, "Invalid Code"

# AI Functions
def get_ai_response(prompt, mode="chat"):
    try:
        # Use Gemini 1.5 Flash for everything to ensure speed and stability
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompts = {
            "chat": "You are an NCERT AI tutor. Provide detailed educational responses.",
            "socratic": "Ask guiding questions, don't give answers. Follow NCERT.",
            "simplify": "Explain like I'm 5 years old. Simple words only.",
        }
        full_prompt = f"{prompts.get(mode, prompts['chat'])}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_image(image_file, prompt="Explain this image"):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        img = Image.open(image_file)
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"Vision Error: {str(e)}"

def summarize_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in pdf_reader.pages])
        return get_ai_response(f"Summarize this in key points:\n\n{text[:10000]}")
    except Exception as e:
        return str(e)

def generate_quiz(subject, difficulty, class_level, topic=None):
    prompt = f"Generate 5 MCQs for {class_level} {subject} {difficulty}. Format: Q1, A), B), C), D), Correct:, Explanation:"
    response = get_ai_response(prompt)
    # Basic parsing logic kept from original
    questions = []
    lines = response.split('\n')
    current = {}
    for line in lines:
        if line.startswith('Q'):
            if current: questions.append(current)
            current = {'question': line, 'options': {}}
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            current['options'][line[0]] = line[2:]
        elif line.startswith('Correct:'):
            current['correct'] = line.split(':')[1].strip()[0]
    if current: questions.append(current)
    return questions

def save_history(user_id, question, answer):
    try:
        supabase.table('history').insert({'user_id': user_id, 'question': question, 'answer': answer}).execute()
    except: pass

# Main UI Routing Logic
if st.session_state.user is None:
    # Logic to show login tabs
    st.title("🎓 AI Study Assistant")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            s, m = login_user(e, p)
            if s: st.rerun()
            else: st.error(m)
    with t2:
        n = st.text_input("Name")
        e_s = st.text_input("Email ")
        p_s = st.text_input("Password ", type="password")
        if st.button("Sign Up"):
            s, m = create_account(e_s, p_s, n)
            if s: st.success(m)
            else: st.error(m)
else:
    # Main App Sidebar
    with st.sidebar:
        st.write(f"Hello, {st.session_state.user['name']}")
        mode = st.selectbox("Mode", ["AI Chat", "Socratic Tutor", "Quiz Generator", "Multimedia Tools"])
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()

    # Feature Routing
    if mode == "AI Chat":
        st.subheader("💬 AI Chat")
        u_in = st.chat_input("Ask me anything...")
        if u_in:
            resp = get_ai_response(u_in)
            st.write(resp)
            save_history(st.session_state.user['uid'], u_in, resp)
            
    elif mode == "Quiz Generator":
        st.subheader("📝 Quiz")
        if st.button("Generate Quiz"):
            st.session_state.quiz_data = generate_quiz("Science", "Medium", "Class 10")
        if 'quiz_data' in st.session_state:
            for i, q in enumerate(st.session_state.quiz_data):
                st.write(q['question'])
                # Fixed Lambda for options
                st.radio("Options", list(q['options'].keys()), format_func=lambda x: f"{x}) {q['options'][x]}", key=f"quiz_{i}")

    elif mode == "Multimedia Tools":
        st.subheader("📸 Vision & PDF")
        up = st.file_uploader("Upload Image or PDF")
        if up:
            if up.type == "application/pdf":
                st.write(summarize_pdf(up))
            else:
                st.image(up)
                st.write(analyze_image(up))
