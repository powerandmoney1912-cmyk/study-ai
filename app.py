import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json
import os
from datetime import datetime
import PyPDF2
import io
from PIL import Image
import base64

# Page Configuration
st.set_page_config(
    page_title="AI Study Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Firebase Admin (only once)
if not firebase_admin._apps:
    # Load Firebase credentials from Streamlit secrets
    firebase_creds = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

# Configure Gemini API
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'study_mode' not in st.session_state:
    st.session_state.study_mode = "AI Chat"
if 'quiz_data' not in st.session_state:
    st.session_state.quiz_data = None
if 'flashcards' not in st.session_state:
    st.session_state.flashcards = []

# NCERT Curriculum Data
NCERT_SUBJECTS = {
    "Mathematics": ["Algebra", "Geometry", "Trigonometry", "Calculus", "Statistics", "Probability"],
    "Science": ["Physics", "Chemistry", "Biology", "Environmental Science"],
    "Social Science": ["History", "Geography", "Political Science", "Economics"],
    "English": ["Grammar", "Literature", "Writing Skills", "Comprehension"],
    "Tamil": ["Grammar", "Literature", "Poetry", "Prose"],
    "Hindi": ["Grammar", "Literature", "Poetry", "Prose"],
    "Marathi": ["Grammar", "Literature", "Poetry", "Prose"]
}

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard", "Expert"]
NCERT_CLASSES = ["Class 6", "Class 7", "Class 8", "Class 9", "Class 10", "Class 11", "Class 12"]

# Custom CSS
st.markdown("""
    <style>
    .main {
        background-color: #f5f7fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 5px solid #2196F3;
    }
    .ai-message {
        background-color: #f1f8e9;
        border-left: 5px solid #4CAF50;
    }
    .flashcard {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    .quiz-option {
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        cursor: pointer;
        background-color: #f0f0f0;
    }
    .quiz-option:hover {
        background-color: #e0e0e0;
    }
    .correct {
        background-color: #c8e6c9 !important;
    }
    .incorrect {
        background-color: #ffcdd2 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Authentication Functions
def sign_up(email, password, name):
    try:
        user = auth.create_user(
            email=email,
            password=password,
            display_name=name
        )
        # Create user document in Firestore
        db.collection('users').document(user.uid).set({
            'name': name,
            'email': email,
            'created_at': datetime.now(),
            'total_questions': 0,
            'study_streak': 0
        })
        return True, "Account created successfully!"
    except Exception as e:
        return False, str(e)

def sign_in(email, password):
    try:
        # Note: Firebase Admin SDK doesn't support password verification
        # You'll need to use Firebase Client SDK or REST API for this
        # For demonstration, we'll create a simple check
        users = auth.list_users().iterate_all()
        for user in users:
            if user.email == email:
                st.session_state.user = {
                    'uid': user.uid,
                    'email': user.email,
                    'name': user.display_name
                }
                return True, "Logged in successfully!"
        return False, "User not found"
    except Exception as e:
        return False, str(e)

# AI Functions
def get_ai_response(prompt, context="", mode="chat"):
    """Get response from Gemini AI based on mode"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_prompts = {
        "chat": "You are a helpful AI study assistant following NCERT curriculum guidelines. Provide clear, accurate, and educational responses.",
        "socratic": "You are a Socratic tutor. Never give direct answers. Instead, ask guiding questions to help the student discover the answer themselves. Follow NCERT curriculum.",
        "simplify": "Explain concepts as if teaching a 5-year-old. Use simple language, analogies, and examples. Follow NCERT curriculum.",
        "quiz": f"Generate quiz questions following NCERT curriculum for {context}. Format: Question, 4 options (A, B, C, D), correct answer, explanation.",
        "flashcard": "Convert the given content into flashcard format. Front: Question/Concept, Back: Answer/Explanation. Follow NCERT curriculum."
    }
    
    full_prompt = f"{system_prompts.get(mode, system_prompts['chat'])}\n\n{prompt}"
    response = model.generate_content(full_prompt)
    return response.text

def analyze_image(image_file, prompt="Analyze this image and explain the concepts"):
    """Analyze uploaded image using Gemini Vision"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    image = Image.open(image_file)
    response = model.generate_content([prompt + " Follow NCERT curriculum guidelines.", image])
    return response.text

def process_pdf(pdf_file):
    """Extract text from PDF and summarize"""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    
    # Summarize using AI
    summary_prompt = f"Summarize this study material in 10 key bullet points following NCERT curriculum:\n\n{text[:8000]}"
    summary = get_ai_response(summary_prompt)
    return summary

def process_audio(audio_file):
    """Process audio file (placeholder - requires additional setup)"""
    # Note: Audio processing requires additional libraries and API setup
    st.warning("Audio processing feature requires additional setup. Please upload audio to a transcription service first.")
    return None

def generate_quiz(subject, difficulty, class_level, topic=None):
    """Generate NCERT-based quiz questions"""
    prompt = f"""
    Generate 5 multiple-choice questions for NCERT {class_level} {subject}.
    Difficulty: {difficulty}
    {f'Topic: {topic}' if topic else ''}
    
    Format each question as:
    Q1: [Question]
    A) [Option A]
    B) [Option B]
    C) [Option C]
    D) [Option D]
    Correct Answer: [A/B/C/D]
    Explanation: [Brief explanation]
    
    Make questions aligned with NCERT curriculum and textbook content.
    """
    
    response = get_ai_response(prompt, mode="quiz", context=f"{subject} - {difficulty} - {class_level}")
    return parse_quiz_response(response)

def parse_quiz_response(response):
    """Parse AI response into structured quiz data"""
    questions = []
    current_q = {}
    
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('Q'):
            if current_q:
                questions.append(current_q)
            current_q = {'question': line.split(':', 1)[1].strip() if ':' in line else line, 'options': {}}
        elif line.startswith(('A)', 'B)', 'C)', 'D)')):
            option = line[0]
            text = line[2:].strip()
            current_q['options'][option] = text
        elif line.startswith('Correct Answer:'):
            current_q['correct'] = line.split(':')[1].strip()[0]
        elif line.startswith('Explanation:'):
            current_q['explanation'] = line.split(':', 1)[1].strip()
    
    if current_q:
        questions.append(current_q)
    
    return questions

def create_flashcards(chat_history):
    """Generate flashcards from chat history"""
    conversation_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history[-10:]])
    prompt = f"Create 5 flashcards from this conversation. Follow NCERT curriculum:\n\n{conversation_text}"
    response = get_ai_response(prompt, mode="flashcard")
    return parse_flashcards(response)

def parse_flashcards(response):
    """Parse AI response into flashcard format"""
    flashcards = []
    lines = response.split('\n')
    current_card = {}
    
    for line in lines:
        line = line.strip()
        if line.startswith(('Front:', 'Question:')):
            if current_card:
                flashcards.append(current_card)
            current_card = {'front': line.split(':', 1)[1].strip()}
        elif line.startswith(('Back:', 'Answer:')):
            current_card['back'] = line.split(':', 1)[1].strip()
    
    if current_card:
        flashcards.append(current_card)
    
    return flashcards

def save_to_history(user_id, question, answer):
    """Save chat to user's history in Firestore"""
    try:
        db.collection('users').document(user_id).collection('history').add({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now(),
            'mode': st.session_state.study_mode
        })
        # Update user stats
        user_ref = db.collection('users').document(user_id)
        user_ref.update({
            'total_questions': firestore.Increment(1)
        })
    except Exception as e:
        st.error(f"Error saving to history: {e}")

def get_user_history(user_id):
    """Retrieve user's chat history"""
    try:
        history = db.collection('users').document(user_id).collection('history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(50).stream()
        return [{'question': h.to_dict()['question'], 'answer': h.to_dict()['answer'], 'timestamp': h.to_dict()['timestamp']} for h in history]
    except Exception as e:
        st.error(f"Error loading history: {e}")
        return []

# UI Components
def show_login_page():
    """Display login/signup page"""
    st.title("🎓 AI Study Assistant")
    st.markdown("### Welcome to Your Personal Learning Companion")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            success, message = sign_in(email, password)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    
    with tab2:
        st.subheader("Create New Account")
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("Sign Up", key="signup_btn"):
            if password != confirm_password:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters!")
            else:
                success, message = sign_up(email, password, name)
                if success:
                    st.success(message)
                    st.info("Please login with your credentials")
                else:
                    st.error(message)

def show_sidebar():
    """Display sidebar with user info and navigation"""
    with st.sidebar:
        st.image("https://img.icons8.com/fluency/96/000000/student-male.png", width=100)
        st.title(f"Welcome, {st.session_state.user['name']}!")
        
        st.markdown("---")
        
        # Study Mode Selection
        st.subheader("📚 Study Mode")
        mode = st.selectbox(
            "Choose your learning mode:",
            ["AI Chat", "Socratic Tutor", "Quiz Generator", "Flashcards", "Simplifier (ELI5)", "Multimedia Tools", "Dashboard"],
            key="mode_selector"
        )
        st.session_state.study_mode = mode
        
        st.markdown("---")
        
        # User Stats
        try:
            user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
            st.metric("Questions Asked", user_data.get('total_questions', 0))
            st.metric("Study Streak", f"{user_data.get('study_streak', 0)} days")
        except:
            pass
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.chat_history = []
            st.rerun()

def show_chat_interface():
    """Main AI chat interface"""
    st.title("💬 AI Study Chat")
    st.caption("Ask me anything about your studies! I follow NCERT curriculum.")
    
    # Display chat history
    for message in st.session_state.chat_history:
        css_class = "user-message" if message['role'] == 'user' else "ai-message"
        st.markdown(f'<div class="chat-message {css_class}"><strong>{message["role"].title()}:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    
    # Chat input
    user_input = st.chat_input("Type your question here...")
    
    if user_input:
        # Add user message
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        # Get AI response
        with st.spinner("Thinking..."):
            response = get_ai_response(user_input)
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            
            # Save to database
            save_to_history(st.session_state.user['uid'], user_input, response)
        
        st.rerun()

def show_socratic_mode():
    """Socratic tutoring mode"""
    st.title("🤔 Socratic Tutor")
    st.caption("I'll guide you to discover answers through questions!")
    
    # Display chat history
    for message in st.session_state.chat_history:
        css_class = "user-message" if message['role'] == 'user' else "ai-message"
        st.markdown(f'<div class="chat-message {css_class}"><strong>{message["role"].title()}:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    
    user_input = st.chat_input("Tell me what you're trying to learn...")
    
    if user_input:
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        with st.spinner("Preparing guiding questions..."):
            response = get_ai_response(user_input, mode="socratic")
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            save_to_history(st.session_state.user['uid'], user_input, response)
        
        st.rerun()

def show_quiz_generator():
    """Quiz generation interface"""
    st.title("📝 NCERT Quiz Generator")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox("Subject", list(NCERT_SUBJECTS.keys()))
    
    with col2:
        class_level = st.selectbox("Class", NCERT_CLASSES)
    
    with col3:
        difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
    
    topic = st.selectbox("Topic (Optional)", ["All Topics"] + NCERT_SUBJECTS[subject])
    
    if st.button("Generate Quiz", use_container_width=True):
        with st.spinner("Generating quiz questions..."):
            topic_str = None if topic == "All Topics" else topic
            st.session_state.quiz_data = generate_quiz(subject, difficulty, class_level, topic_str)
            st.session_state.quiz_answers = {}
    
    # Display quiz
    if st.session_state.quiz_data:
        st.markdown("---")
        st.subheader("Answer the following questions:")
        
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Question {idx + 1}:** {q['question']}")
            
            answer = st.radio(
                "Select your answer:",
                options=list(q['options'].keys()),
                format_func=lambda x: f"{x}) {q['options'][x]}",
                key=f"q_{idx}"
            )
            
            st.session_state.quiz_answers[idx] = answer
            st.markdown("---")
        
        if st.button("Submit Quiz", use_container_width=True):
            score = 0
            st.markdown("### Results:")
            
            for idx, q in enumerate(st.session_state.quiz_data):
                user_answer = st.session_state.quiz_answers.get(idx)
                is_correct = user_answer == q['correct']
                
                if is_correct:
                    score += 1
                    st.success(f"✅ Question {idx + 1}: Correct!")
                else:
                    st.error(f"❌ Question {idx + 1}: Incorrect")
                    st.info(f"Correct answer: {q['correct']}) {q['options'][q['correct']]}")
                
                if 'explanation' in q:
                    st.caption(f"💡 {q['explanation']}")
                st.markdown("---")
            
            percentage = (score / len(st.session_state.quiz_data)) * 100
            st.markdown(f"## Final Score: {score}/{len(st.session_state.quiz_data)} ({percentage:.1f}%)")
            
            if percentage >= 80:
                st.balloons()
                st.success("Excellent work! 🎉")
            elif percentage >= 60:
                st.info("Good job! Keep practicing! 💪")
            else:
                st.warning("Keep studying! You'll do better next time! 📚")

def show_flashcards():
    """Flashcard interface"""
    st.title("🎴 Flashcard Creator")
    
    if st.button("Generate Flashcards from Chat", use_container_width=True):
        if len(st.session_state.chat_history) < 2:
            st.warning("Have a conversation first to generate flashcards!")
        else:
            with st.spinner("Creating flashcards..."):
                st.session_state.flashcards = create_flashcards(st.session_state.chat_history)
    
    # Display flashcards
    if st.session_state.flashcards:
        st.markdown("### Your Flashcards:")
        
        for idx, card in enumerate(st.session_state.flashcards):
            with st.expander(f"📇 Flashcard {idx + 1}"):
                st.markdown(f"**Front:** {card['front']}")
                st.markdown(f"**Back:** {card['back']}")

def show_simplifier():
    """ELI5 mode"""
    st.title("🧒 Simplifier (Explain Like I'm 5)")
    st.caption("Complex topics explained in the simplest way possible!")
    
    for message in st.session_state.chat_history:
        css_class = "user-message" if message['role'] == 'user' else "ai-message"
        st.markdown(f'<div class="chat-message {css_class}"><strong>{message["role"].title()}:</strong> {message["content"]}</div>', unsafe_allow_html=True)
    
    user_input = st.chat_input("What topic should I explain simply?")
    
    if user_input:
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        with st.spinner("Simplifying..."):
            response = get_ai_response(user_input, mode="simplify")
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            save_to_history(st.session_state.user['uid'], user_input, response)
        
        st.rerun()

def show_multimedia_tools():
    """Multimedia analysis tools"""
    st.title("🎨 Multimedia AI Tools")
    
    tab1, tab2, tab3 = st.tabs(["📷 Image Analysis", "📄 PDF Summary", "🎵 Audio Transcript"])
    
    with tab1:
        st.subheader("Upload Image for Analysis")
        st.caption("Upload textbook pages, handwritten notes, diagrams, or math problems")
        
        uploaded_image = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg', 'webp'])
        custom_prompt = st.text_input("Custom prompt (optional)", "Analyze this image and explain the concepts")
        
        if uploaded_image:
            st.image(uploaded_image, caption="Uploaded Image", use_container_width=True)
            
            if st.button("Analyze Image", use_container_width=True):
                with st.spinner("Analyzing image..."):
                    result = analyze_image(uploaded_image, custom_prompt)
                    st.markdown("### Analysis:")
                    st.markdown(result)
                    save_to_history(st.session_state.user['uid'], "Image Analysis", result)
    
    with tab2:
        st.subheader("PDF Summarization")
        st.caption("Upload study guides, textbooks, or notes for instant summaries")
        
        uploaded_pdf = st.file_uploader("Choose a PDF", type=['pdf'])
        
        if uploaded_pdf:
            if st.button("Summarize PDF", use_container_width=True):
                with st.spinner("Processing PDF..."):
                    summary = process_pdf(uploaded_pdf)
                    st.markdown("### Summary:")
                    st.markdown(summary)
                    save_to_history(st.session_state.user['uid'], "PDF Summary", summary)
    
    with tab3:
        st.subheader("Audio Transcription")
        st.caption("Upload lecture recordings for transcripts and notes")
        
        uploaded_audio = st.file_uploader("Choose an audio file", type=['mp3', 'wav', 'm4a'])
        
        if uploaded_audio:
            st.audio(uploaded_audio)
            
            if st.button("Transcribe Audio", use_container_width=True):
                st.info("Audio transcription requires additional API setup. Please use a dedicated transcription service.")

def show_dashboard():
    """User dashboard with history and stats"""
    st.title("📊 Your Learning Dashboard")
    
    # User stats
    try:
        user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Questions", user_data.get('total_questions', 0))
        with col2:
            st.metric("Study Streak", f"{user_data.get('study_streak', 0)} days")
        with col3:
            st.metric("Member Since", user_data.get('created_at').strftime('%B %Y') if 'created_at' in user_data else 'N/A')
        
        st.markdown("---")
        
        # Chat history
        st.subheader("📚 Recent Study History")
        history = get_user_history(st.session_state.user['uid'])
        
        if history:
            for item in history[:10]:
                with st.expander(f"❓ {item['question'][:100]}..." if len(item['question']) > 100 else f"❓ {item['question']}"):
                    st.caption(f"Date: {item['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                    st.markdown(f"**Answer:** {item['answer']}")
        else:
            st.info("No study history yet. Start chatting with your AI tutor!")
    
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

# Main App Logic
def main():
    if st.session_state.user is None:
        show_login_page()
    else:
        show_sidebar()
        
        # Route to appropriate interface based on study mode
        if st.session_state.study_mode == "AI Chat":
            show_chat_interface()
        elif st.session_state.study_mode == "Socratic Tutor":
            show_socratic_mode()
        elif st.session_state.study_mode == "Quiz Generator":
            show_quiz_generator()
        elif st.session_state.study_mode == "Flashcards":
            show_flashcards()
        elif st.session_state.study_mode == "Simplifier (ELI5)":
            show_simplifier()
        elif st.session_state.study_mode == "Multimedia Tools":
            show_multimedia_tools()
        elif st.session_state.study_mode == "Dashboard":
            show_dashboard()

if __name__ == "__main__":
    main()
