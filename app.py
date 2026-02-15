import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime
import PyPDF2
from PIL import Image
import json

# Page Configuration
st.set_page_config(page_title="AI Study Assistant", page_icon="🎓", layout="wide")

# Initialize Firebase with better error handling
if not firebase_admin._apps:
    try:
        # Method 1: Try direct dict conversion
        firebase_config = dict(st.secrets["firebase"])
        
        # Fix the private_key - remove any extra escaping
        if "private_key" in firebase_config:
            # Replace literal \n with actual newlines
            firebase_config["private_key"] = firebase_config["private_key"].replace("\\n", "\n")
        
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Firebase initialization error: {str(e)}")
        st.info("Please check your Firebase credentials in secrets")
        st.stop()

db = firestore.client()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# PREMIUM CODES
PREMIUM_CODES = {
    "PREMIUM2024": "Valid until Dec 2024",
    "STUDENT100": "Student Special Access",
    "TEACHER50": "Teacher Premium",
    "LIFETIME": "Lifetime Premium Access"
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
        user = auth.create_user(email=email, password=password, display_name=name)
        db.collection('users').document(user.uid).set({
            'name': name, 
            'email': email, 
            'created_at': datetime.now(), 
            'total_questions': 0,
            'is_premium': False,
            'premium_activated_at': None
        })
        return True, "Account created successfully!"
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return False, "This email is already registered!"
        elif "INVALID_EMAIL" in error_msg:
            return False, "Invalid email address!"
        elif "WEAK_PASSWORD" in error_msg:
            return False, "Password is too weak. Use at least 6 characters!"
        return False, f"Error: {error_msg}"

def login_user(email, password):
    try:
        users = auth.list_users().iterate_all()
        for user in users:
            if user.email == email:
                # Get premium status
                user_doc = db.collection('users').document(user.uid).get()
                is_premium = user_doc.to_dict().get('is_premium', False) if user_doc.exists else False
                
                st.session_state.user = {
                    'uid': user.uid, 
                    'email': user.email, 
                    'name': user.display_name or 'User'
                }
                st.session_state.is_premium = is_premium
                return True, "Login successful!"
        return False, "User not found. Please check your email or sign up."
    except Exception as e:
        return False, f"Login error: {str(e)}"

def activate_premium(code):
    """Activate premium with code"""
    if code in PREMIUM_CODES:
        try:
            db.collection('users').document(st.session_state.user['uid']).update({
                'is_premium': True,
                'premium_activated_at': datetime.now(),
                'premium_code_used': code
            })
            st.session_state.is_premium = True
            return True, f"✅ Premium Activated! {PREMIUM_CODES[code]}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    else:
        return False, "❌ Invalid premium code!"

# AI Functions
def get_ai_response(prompt, mode="chat"):
    try:
        # Premium: Gemini 1.5 Flash, Free: Gemini Pro
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
            if current: questions.append(current)
            current = {'question': line.split(':', 1)[1].strip() if ':' in line else line, 'options': {}}
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            current['options'][line[0]] = line[2:].strip()
        elif line.startswith('Correct:'):
            current['correct'] = line.split(':')[1].strip()[0]
        elif line.startswith('Explanation:'):
            current['explanation'] = line.split(':', 1)[1].strip()
    
    if current: questions.append(current)
    return questions

def save_history(user_id, question, answer):
    try:
        db.collection('users').document(user_id).collection('history').add({
            'question': question, 
            'answer': answer, 
            'timestamp': datetime.now(),
            'model_used': 'premium' if st.session_state.is_premium else 'free'
        })
        db.collection('users').document(user_id).update({'total_questions': firestore.Increment(1)})
    except: 
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
        
        st.title(f"👋 {st.session_state.user['name']}")
        
        if not st.session_state.is_premium:
            st.markdown("---")
            with st.expander("🌟 Upgrade to Premium", expanded=False):
                st.write("**Benefits:**")
                st.write("✅ Gemini 1.5 Flash (Faster)")
                st.write("✅ 10 Quiz Questions")
                st.write("✅ Detailed Summaries")
                
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
            user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
            st.metric("Questions", user_data.get('total_questions', 0))
        except:
            pass
        
        st.caption("🇮🇳 NCERT Aligned")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.chat_history = []
            st.session_state.is_premium = False
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
                with st.spinner("Analyzing..."):
                    result = analyze_image(uploaded_img)
                    st.markdown(result)
    
    with tab2:
        uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'])
        if uploaded_pdf and st.button("Summarize"):
            with st.spinner("Processing..."):
                summary = summarize_pdf(uploaded_pdf)
                st.markdown(summary)

def show_dashboard():
    st.title("📊 Dashboard")
    
    try:
        user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Questions", user_data.get('total_questions', 0))
        with col2:
            st.metric("Status", "👑 Premium" if st.session_state.is_premium else "🔓 Free")
        
        st.markdown("---")
        st.subheader("Recent History")
        
        history = db.collection('users').document(st.session_state.user['uid']).collection('history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        
        for item in history:
            data = item.to_dict()
            with st.expander(f"❓ {data['question'][:80]}..."):
                st.markdown(f"**Q:** {data['question']}")
                st.markdown(f"**A:** {data['answer']}")
                st.caption(data['timestamp'].strftime('%Y-%m-%d %H:%M'))
    except:
        st.info("Start using the app to see stats!")

# Main
def main():
    if not st.session_state.user:
        show_login()
    else:
        show_sidebar()
        
        if st.session_state.study_mode == "AI Chat":
            show_chat("chat")
        elif st.session_state.study_mode == "Socratic Tutor":
            show_chat("socratic")
        elif st.session_state.study_mode == "Simplifier":
            show_chat("simplify")
        elif st.session_state.study_mode == "Quiz Generator":
            show_quiz()
        elif st.session_state.study_mode == "Multimedia Tools":
            show_multimedia()
        elif st.session_state.study_mode == "Dashboard":
            show_dashboard()

if __name__ == "__main__":
    main()
