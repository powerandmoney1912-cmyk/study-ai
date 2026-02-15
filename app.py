import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
from datetime import datetime
import PyPDF2
from PIL import Image

# Page Configuration
st.set_page_config(page_title="AI Study Assistant", page_icon="🎓", layout="wide")

# Initialize Firebase (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'study_mode' not in st.session_state:
    st.session_state.study_mode = "AI Chat"

# NCERT Configuration
NCERT_SUBJECTS = {
    "Mathematics": ["Algebra", "Geometry", "Trigonometry", "Calculus"],
    "Science": ["Physics", "Chemistry", "Biology"],
    "Social Science": ["History", "Geography", "Political Science"],
    "English": ["Grammar", "Literature", "Writing"],
    "Tamil": ["Grammar", "Literature"],
    "Hindi": ["Grammar", "Literature"],
    "Marathi": ["Grammar", "Literature"]
}
DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard", "Expert"]
NCERT_CLASSES = ["Class 6", "Class 7", "Class 8", "Class 9", "Class 10", "Class 11", "Class 12"]

# Custom CSS
st.markdown("""<style>
    .stButton>button {width: 100%; background-color: #4CAF50; color: white;}
    .chat-message {padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem;}
    .user-message {background-color: #e3f2fd; border-left: 5px solid #2196F3;}
    .ai-message {background-color: #f1f8e9; border-left: 5px solid #4CAF50;}
</style>""", unsafe_allow_html=True)

# Authentication Functions
def create_account(email, password, name):
    try:
        user = auth.create_user(email=email, password=password, display_name=name)
        db.collection('users').document(user.uid).set({
            'name': name, 'email': email, 'created_at': datetime.now(), 'total_questions': 0
        })
        return True, "Account created!"
    except Exception as e:
        return False, str(e)

def login_user(email, password):
    try:
        # Simple check - in production, use Firebase Client SDK
        users = auth.list_users().iterate_all()
        for user in users:
            if user.email == email:
                st.session_state.user = {'uid': user.uid, 'email': user.email, 'name': user.display_name}
                return True, "Login successful!"
        return False, "User not found"
    except Exception as e:
        return False, str(e)

# AI Functions with error handling
def get_ai_response(prompt, mode="chat"):
    try:
        # Try gemini-pro first (most stable)
        model = genai.GenerativeModel('gemini-pro')
        prompts = {
            "chat": "You are an NCERT-aligned AI tutor. Provide clear educational responses.",
            "socratic": "You are a Socratic tutor. Ask guiding questions, never give direct answers.",
            "simplify": "Explain like I'm 5 years old. Use simple words and fun examples.",
        }
        full_prompt = f"{prompts.get(mode, prompts['chat'])}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return "Sorry, I encountered an error. Please try again or check your API key."

def analyze_image(image_file, prompt="Explain this image"):
    try:
        model = genai.GenerativeModel('gemini-pro-vision')
        image = Image.open(image_file)
        response = model.generate_content([prompt + " Follow NCERT curriculum.", image])
        return response.text
    except Exception as e:
        st.error(f"Image analysis error: {str(e)}")
        return "Sorry, I couldn't analyze the image. Please try again."

def summarize_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in pdf_reader.pages])
        return get_ai_response(f"Summarize in 10 key points:\n\n{text[:8000]}")
    except Exception as e:
        st.error(f"PDF error: {str(e)}")
        return "Sorry, couldn't process the PDF."

def generate_quiz(subject, difficulty, class_level, topic=None):
    prompt = f"""Generate 5 NCERT {class_level} {subject} MCQs ({difficulty} level).
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
            'question': question, 'answer': answer, 'timestamp': datetime.now()
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
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            success, msg = login_user(email, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
    with tab2:
        name = st.text_input("Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Sign Up"):
            if len(password) < 6:
                st.error("Password must be 6+ characters")
            else:
                success, msg = create_account(email, password, name)
                st.success(msg) if success else st.error(msg)

def show_sidebar():
    with st.sidebar:
        st.title(f"👋 {st.session_state.user['name']}")
        st.session_state.study_mode = st.selectbox("Study Mode", 
            ["AI Chat", "Socratic Tutor", "Quiz Generator", "Simplifier", "Multimedia Tools", "Dashboard"])
        
        st.markdown("---")
        st.caption("NCERT Curriculum Aligned")
        
        if st.button("🚪 Logout"):
            st.session_state.user = None
            st.session_state.chat_history = []
            st.rerun()

def show_chat(mode="chat"):
    title_map = {
        "chat": "💬 AI Study Chat",
        "socratic": "🤔 Socratic Tutor",
        "simplify": "🧒 Simplifier (ELI5)"
    }
    st.title(title_map.get(mode, "💬 Chat"))
    
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

def show_quiz():
    st.title("📝 NCERT Quiz Generator")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox("Subject", list(NCERT_SUBJECTS.keys()))
    with col2:
        class_level = st.selectbox("Class", NCERT_CLASSES)
    with col3:
        difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
    
    topic = st.selectbox("Topic", ["All Topics"] + NCERT_SUBJECTS[subject])
    
    if st.button("Generate Quiz"):
        with st.spinner("Creating questions..."):
            st.session_state.quiz_data = generate_quiz(subject, difficulty, class_level, 
                                                       None if topic == "All Topics" else topic)
            st.session_state.quiz_answers = {}
    
    if 'quiz_data' in st.session_state and st.session_state.quiz_data:
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Q{idx+1}:** {q['question']}")
            answer = st.radio("", list(q['options'].keys()), 
                            format_func=lambda x: f"{x}) {q['options'][x]}", key=f"q_{idx}")
            st.session_state.quiz_answers[idx] = answer
            st.markdown("---")
        
        if st.button("Submit Quiz"):
            score = sum(1 for idx, q in enumerate(st.session_state.quiz_data) 
                       if st.session_state.quiz_answers.get(idx) == q['correct'])
            percentage = (score / len(st.session_state.quiz_data)) * 100
            
            st.markdown("### 📊 Results:")
            for idx, q in enumerate(st.session_state.quiz_data):
                is_correct = st.session_state.quiz_answers.get(idx) == q['correct']
                if is_correct:
                    st.success(f"✅ Q{idx+1}: Correct!")
                else:
                    st.error(f"❌ Q{idx+1}: Wrong. Answer: {q['correct']}) {q['options'][q['correct']]}")
                if 'explanation' in q:
                    st.caption(f"💡 {q['explanation']}")
            
            st.markdown(f"## Score: {score}/{len(st.session_state.quiz_data)} ({percentage:.0f}%)")
            if percentage >= 80:
                st.balloons()
                st.success("🎉 Excellent work!")
            elif percentage >= 60:
                st.info("💪 Good job! Keep practicing!")
            else:
                st.warning("📚 Keep studying! You'll do better next time!")

def show_multimedia():
    st.title("🎨 Multimedia Tools")
    tab1, tab2 = st.tabs(["📷 Image Analysis", "📄 PDF Summary"])
    
    with tab1:
        st.subheader("Upload an Image")
        st.caption("Upload textbook pages, diagrams, or handwritten problems")
        uploaded_img = st.file_uploader("Choose image", type=['png', 'jpg', 'jpeg'])
        if uploaded_img:
            st.image(uploaded_img, width=400)
            if st.button("Analyze Image"):
                with st.spinner("Analyzing..."):
                    result = analyze_image(uploaded_img)
                    st.markdown("### Analysis:")
                    st.markdown(result)
    
    with tab2:
        st.subheader("Upload a PDF")
        st.caption("Get key points from study guides and textbooks")
        uploaded_pdf = st.file_uploader("Choose PDF", type=['pdf'])
        if uploaded_pdf and st.button("Summarize PDF"):
            with st.spinner("Processing..."):
                summary = summarize_pdf(uploaded_pdf)
                st.markdown("### Summary:")
                st.markdown(summary)

def show_dashboard():
    st.title("📊 Your Dashboard")
    try:
        user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📚 Questions Asked", user_data.get('total_questions', 0))
        with col2:
            st.metric("📅 Member Since", user_data.get('created_at', datetime.now()).strftime('%B %Y'))
        
        st.markdown("---")
        st.subheader("📝 Recent Questions")
        
        history = db.collection('users').document(st.session_state.user['uid']).collection('history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        
        for item in history:
            data = item.to_dict()
            question_preview = data['question'][:80] + "..." if len(data['question']) > 80 else data['question']
            with st.expander(f"❓ {question_preview}"):
                st.markdown(f"**Question:** {data['question']}")
                st.markdown(f"**Answer:** {data['answer']}")
                st.caption(f"⏰ {data['timestamp'].strftime('%Y-%m-%d %H:%M')}")
    except Exception as e:
        st.info("Start using the app to see your stats!")
        st.caption(f"Debug: {str(e)}")

# Main App
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
