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

# PREMIUM CODES - Add your codes here
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
    .premium-feature {
        border: 2px solid #FFD700;
        padding: 10px;
        border-radius: 10px;
        background-color: #FFFACD;
    }
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
        return True, "Account created!"
    except Exception as e:
        return False, str(e)

def login_user(email, password):
    try:
        users = auth.list_users().iterate_all()
        for user in users:
            if user.email == email:
                # Get premium status from Firestore
                user_doc = db.collection('users').document(user.uid).get()
                is_premium = user_doc.to_dict().get('is_premium', False) if user_doc.exists else False
                
                st.session_state.user = {
                    'uid': user.uid, 
                    'email': user.email, 
                    'name': user.display_name
                }
                st.session_state.is_premium = is_premium
                return True, "Login successful!"
        return False, "User not found"
    except Exception as e:
        return False, str(e)

def activate_premium(code):
    """Activate premium with code"""
    if code in PREMIUM_CODES:
        try:
            # Update Firestore
            db.collection('users').document(st.session_state.user['uid']).update({
                'is_premium': True,
                'premium_activated_at': datetime.now(),
                'premium_code_used': code
            })
            st.session_state.is_premium = True
            return True, f"✅ Premium Activated! {PREMIUM_CODES[code]}"
        except Exception as e:
            return False, f"Error activating premium: {str(e)}"
    else:
        return False, "❌ Invalid premium code!"

# AI Functions with Premium/Free models
def get_ai_response(prompt, mode="chat"):
    try:
        # Premium users get Gemini 1.5 Flash (faster, better)
        # Free users get Gemini Pro (standard)
        if st.session_state.is_premium:
            model = genai.GenerativeModel('gemini-1.5-flash')
            model_name = "⚡ Gemini 1.5 Flash"
        else:
            model = genai.GenerativeModel('gemini-pro')
            model_name = "Gemini Pro"
        
        prompts = {
            "chat": "You are an NCERT-aligned AI tutor. Provide clear, detailed educational responses.",
            "socratic": "You are a Socratic tutor following NCERT curriculum. Ask guiding questions, never give direct answers.",
            "simplify": "Explain like I'm 5 years old using NCERT curriculum. Use simple words and fun examples.",
        }
        full_prompt = f"{prompts.get(mode, prompts['chat'])}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        
        # Add model indicator for premium users
        footer = f"\n\n*Powered by {model_name}*" if st.session_state.is_premium else ""
        return response.text + footer
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return "Sorry, I encountered an error. Please try again."

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
        st.error(f"Image analysis error: {str(e)}")
        return "Sorry, I couldn't analyze the image. Please try again."

def summarize_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = "".join([page.extract_text() for page in pdf_reader.pages])
        
        # Premium users get more detailed summaries
        if st.session_state.is_premium:
            prompt = f"Provide a detailed summary with 15 key points and important concepts:\n\n{text[:12000]}"
        else:
            prompt = f"Summarize in 10 key points:\n\n{text[:8000]}"
        
        return get_ai_response(prompt)
    except Exception as e:
        st.error(f"PDF error: {str(e)}")
        return "Sorry, couldn't process the PDF."

def generate_quiz(subject, difficulty, class_level, topic=None):
    # Premium users get more questions
    num_questions = 10 if st.session_state.is_premium else 5
    
    prompt = f"""Generate {num_questions} NCERT {class_level} {subject} MCQs ({difficulty} level).
    {f'Topic: {topic}' if topic else ''}
    Format each question as:
    Q1: [Question]
    A) [Option]
    B) [Option]
    C) [Option]
    D) [Option]
    Correct: [A/B/C/D]
    Explanation: [Brief explanation]
    
    Make questions strictly aligned with NCERT curriculum."""
    
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
    st.caption("NCERT-Aligned Learning Platform with Premium Features")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="btn_login"):
            success, msg = login_user(email, password)
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
    
    with tab2:
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
        
        if st.button("Sign Up", key="btn_signup"):
            if password != confirm:
                st.error("Passwords don't match!")
            elif len(password) < 6:
                st.error("Password must be 6+ characters")
            else:
                success, msg = create_account(email, password, name)
                if success:
                    st.success(msg)
                    st.info("Please login with your credentials")
                else:
                    st.error(msg)

def show_sidebar():
    with st.sidebar:
        # User info with premium badge
        if st.session_state.is_premium:
            st.markdown('<div class="premium-badge">👑 PREMIUM USER</div>', unsafe_allow_html=True)
        
        st.title(f"👋 {st.session_state.user['name']}")
        
        # Premium activation section
        if not st.session_state.is_premium:
            st.markdown("---")
            st.subheader("🌟 Upgrade to Premium")
            st.info("Enter a premium code to unlock:")
            st.write("✅ Gemini 1.5 Flash (Faster AI)")
            st.write("✅ 10 Quiz Questions (vs 5)")
            st.write("✅ Detailed PDF Summaries")
            st.write("✅ Priority Support")
            
            premium_code = st.text_input("Enter Premium Code", type="password", key="premium_code_input")
            if st.button("Activate Premium", key="activate_premium_btn"):
                success, msg = activate_premium(premium_code)
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        
        st.markdown("---")
        st.subheader("📚 Study Mode")
        st.session_state.study_mode = st.selectbox(
            "Choose your mode:",
            ["AI Chat", "Socratic Tutor", "Quiz Generator", "Simplifier", "Multimedia Tools", "Dashboard"],
            key="mode_selector"
        )
        
        st.markdown("---")
        
        # Display stats
        try:
            user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
            st.metric("📝 Questions", user_data.get('total_questions', 0))
        except:
            pass
        
        st.caption("🇮🇳 NCERT Curriculum Aligned")
        
        if st.button("🚪 Logout", key="logout_btn"):
            st.session_state.user = None
            st.session_state.chat_history = []
            st.session_state.is_premium = False
            st.rerun()

def show_chat(mode="chat"):
    title_map = {
        "chat": "💬 AI Study Chat",
        "socratic": "🤔 Socratic Tutor",
        "simplify": "🧒 Simplifier (ELI5)"
    }
    st.title(title_map.get(mode, "💬 Chat"))
    
    # Show premium indicator
    if st.session_state.is_premium:
        st.success("⚡ Using Gemini 1.5 Flash - Faster & Smarter!")
    else:
        st.info("💡 Upgrade to Premium for Gemini 1.5 Flash!")
    
    for msg in st.session_state.chat_history:
        css = "user-message" if msg['role'] == 'user' else "ai-message"
        st.markdown(f'<div class="chat-message {css}"><b>{msg["role"].title()}:</b> {msg["content"]}</div>', 
                   unsafe_allow_html=True)
    
    user_input = st.chat_input("Ask anything about your studies...")
    if user_input:
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        with st.spinner("Thinking..."):
            response = get_ai_response(user_input, mode)
            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            save_history(st.session_state.user['uid'], user_input, response)
        st.rerun()
    
    # Clear chat button
    if len(st.session_state.chat_history) > 0:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

def show_quiz():
    st.title("📝 NCERT Quiz Generator")
    
    # Premium indicator
    if st.session_state.is_premium:
        st.success("👑 Premium: Get 10 questions per quiz!")
    else:
        st.info("Free: 5 questions per quiz. Upgrade to Premium for 10 questions!")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        subject = st.selectbox("Subject", list(NCERT_SUBJECTS.keys()))
    with col2:
        class_level = st.selectbox("Class", NCERT_CLASSES)
    with col3:
        difficulty = st.selectbox("Difficulty", DIFFICULTY_LEVELS)
    
    topic = st.selectbox("Topic", ["All Topics"] + NCERT_SUBJECTS[subject])
    
    if st.button("🎯 Generate Quiz", key="gen_quiz_btn"):
        with st.spinner("Creating NCERT-aligned questions..."):
            st.session_state.quiz_data = generate_quiz(
                subject, difficulty, class_level, 
                None if topic == "All Topics" else topic
            )
            st.session_state.quiz_answers = {}
    
    if 'quiz_data' in st.session_state and st.session_state.quiz_data:
        st.markdown("---")
        for idx, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Question {idx+1}:** {q['question']}")
            answer = st.radio(
                "Select your answer:",
                list(q['options'].keys()), 
                format_func=lambda x: f"{x}) {q['options'][x]}", 
                key=f"q_{idx}"
            )
            st.session_state.quiz_answers[idx] = answer
            st.markdown("---")
        
        if st.button("✅ Submit Quiz", key="submit_quiz_btn"):
            score = sum(1 for idx, q in enumerate(st.session_state.quiz_data) 
                       if st.session_state.quiz_answers.get(idx) == q['correct'])
            percentage = (score / len(st.session_state.quiz_data)) * 100
            
            st.markdown("### 📊 Quiz Results:")
            for idx, q in enumerate(st.session_state.quiz_data):
                is_correct = st.session_state.quiz_answers.get(idx) == q['correct']
                if is_correct:
                    st.success(f"✅ Question {idx+1}: Correct!")
                else:
                    st.error(f"❌ Question {idx+1}: Wrong")
                    st.info(f"Correct Answer: {q['correct']}) {q['options'][q['correct']]}")
                if 'explanation' in q:
                    st.caption(f"💡 Explanation: {q['explanation']}")
            
            st.markdown(f"## 🎯 Final Score: {score}/{len(st.session_state.quiz_data)} ({percentage:.0f}%)")
            
            if percentage >= 80:
                st.balloons()
                st.success("🎉 Excellent work! You've mastered this topic!")
            elif percentage >= 60:
                st.info("💪 Good job! Keep practicing to improve!")
            else:
                st.warning("📚 Keep studying! Review the concepts and try again!")

def show_multimedia():
    st.title("🎨 Multimedia AI Tools")
    
    if st.session_state.is_premium:
        st.success("👑 Premium: Enhanced image & PDF analysis!")
    
    tab1, tab2 = st.tabs(["📷 Image Analysis", "📄 PDF Summary"])
    
    with tab1:
        st.subheader("Upload an Image")
        st.caption("Analyze textbook pages, diagrams, handwritten notes, or math problems")
        
        uploaded_img = st.file_uploader("Choose image file", type=['png', 'jpg', 'jpeg', 'webp'])
        custom_prompt = st.text_input(
            "Custom instruction (optional)", 
            "Explain this image in detail following NCERT curriculum"
        )
        
        if uploaded_img:
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded_img, caption="Uploaded Image", use_container_width=True)
            
            with col2:
                if st.button("🔍 Analyze Image", key="analyze_img_btn"):
                    with st.spinner("Analyzing image..."):
                        result = analyze_image(uploaded_img, custom_prompt)
                        st.markdown("### 📝 Analysis:")
                        st.markdown(result)
    
    with tab2:
        st.subheader("Upload a PDF")
        if st.session_state.is_premium:
            st.caption("Premium: Get 15 detailed points with concepts (up to 12,000 chars)")
        else:
            st.caption("Free: Get 10 key points (up to 8,000 chars)")
        
        uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'])
        
        if uploaded_pdf:
            st.info(f"📄 File: {uploaded_pdf.name} ({uploaded_pdf.size} bytes)")
            
            if st.button("📋 Summarize PDF", key="summarize_pdf_btn"):
                with st.spinner("Processing PDF... This may take a moment..."):
                    summary = summarize_pdf(uploaded_pdf)
                    st.markdown("### 📝 Summary:")
                    st.markdown(summary)

def show_dashboard():
    st.title("📊 Your Learning Dashboard")
    
    try:
        user_data = db.collection('users').document(st.session_state.user['uid']).get().to_dict()
        
        # Premium status
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.is_premium:
                st.markdown('<div class="premium-badge">👑 PREMIUM</div>', unsafe_allow_html=True)
            else:
                st.warning("🔓 FREE PLAN")
        
        with col2:
            st.metric("📚 Total Questions", user_data.get('total_questions', 0))
        
        with col3:
            member_since = user_data.get('created_at', datetime.now()).strftime('%B %Y')
            st.metric("📅 Member Since", member_since)
        
        st.markdown("---")
        
        # Premium activation info
        if st.session_state.is_premium:
            st.success(f"✅ Premium activated on: {user_data.get('premium_activated_at', datetime.now()).strftime('%Y-%m-%d')}")
        
        # Recent history
        st.subheader("📝 Recent Study History")
        
        history = db.collection('users').document(st.session_state.user['uid']).collection('history').order_by('timestamp', direction=firestore.Query.DESCENDING).limit(20).stream()
        
        count = 0
        for item in history:
            data = item.to_dict()
            question_preview = data['question'][:100] + "..." if len(data['question']) > 100 else data['question']
            
            with st.expander(f"❓ {question_preview}"):
                st.markdown(f"**Question:** {data['question']}")
                st.markdown(f"**Answer:** {data['answer']}")
                st.caption(f"⏰ {data['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                
                model_badge = "👑 Premium" if data.get('model_used') == 'premium' else "🔓 Free"
                st.caption(f"Model: {model_badge}")
            count += 1
        
        if count == 0:
            st.info("No study history yet. Start chatting with your AI tutor!")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")
        st.info("Start using the app to see your statistics!")

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
