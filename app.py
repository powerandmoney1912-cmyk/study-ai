import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 1. INITIALIZE FIREBASE (Pro Login) ---
if not firebase_admin._apps:
    try:
        # Fetches keys from Streamlit Secrets
        fb_creds = dict(st.secrets["firebase"])
        cred = credentials.Certificate(fb_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error("Firebase Secrets missing! Please check your Streamlit Settings.")
        st.stop()

# --- 2. SETUP & SEO ---
st.set_page_config(page_title="Study Master Pro", layout="wide", page_icon="🧠")
# Google Verification Tag
st.markdown('<meta name="google-site-verification" content="ThWp6_7rt4Q973HycJ07l-jYZ0o55s8f0Em28jBBNoU" />', unsafe_allow_html=True)

# Gemini API Setup
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("Google API Key missing in Secrets!")
    st.stop()

# --- 3. SESSION STATE ---
if 'user' not in st.session_state: st.session_state.user = None
if 'is_premium' not in st.session_state: st.session_state.is_premium = False
if 'usage_count' not in st.session_state: st.session_state.usage_count = 0
if 'messages' not in st.session_state: st.session_state.messages = []

# --- 4. LOGIN GATE ---
if st.session_state.user is None:
    st.title("🔐 Study Master Pro: Access")
    choice = st.selectbox("Login or Register", ["Login", "Register"])
    
    email_input = st.text_input("Email")
    pass_input = st.text_input("Password", type="password")
    
    if choice == "Login":
        if st.button("Sign In", use_container_width=True):
            try:
                # Backend check for existing user
                user = auth.get_user_by_email(email_input)
                st.session_state.user = user.email
                st.success("Logged in successfully!")
                st.rerun()
            except:
                st.error("User not found or incorrect details.")
    else:
        if st.button("Create Account", use_container_width=True):
            try:
                auth.create_user(email=email_input, password=pass_input)
                st.success("Account created! You can now switch to Login.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    st.stop()

# --- 5. SIDEBAR (Mobile Optimized) ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    st.write(f"Logged in as: **{st.session_state.user}**")
    
    # Premium Section (Form-based for Mobile 'Enter' key support)
    st.divider()
    st.subheader("💎 Premium Access")
    if not st.session_state.is_premium:
        with st.form("premium_form", clear_on_submit=True):
            promo_code = st.text_input("Enter Premium Code", type="password")
            submit_btn = st.form_submit_button("Submit & Activate ✅", use_container_width=True)
            if submit_btn:
                if promo_code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Pro Activated! 🚀")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Invalid Code.")
    else:
        st.success("✨ PRO STATUS: ACTIVE")

    st.divider()
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan"])
    
    if st.button("Logout 🚪", use_container_width=True):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

# --- 6. HELPER FUNCTIONS ---
def process_pdf(file):
    reader = PdfReader(file)
    text = "".join([page.extract_text() or "" for page in reader.pages])
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=API_KEY)
    return FAISS.from_texts(chunks, embedding=embeddings)

def call_ai(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model.generate_content(prompt).text

# --- 7. MAIN PAGES ---

# --- PAGE: CHAT ---
if menu == "💬 Chat":
    st.header("💬 Chat with your Notes")
    
    # Usage Limiter
    if not st.session_state.is_premium and st.session_state.usage_count >= 5:
        st.warning("⚠️ Free limit reached (5/5). Activate Pro to ask more questions!")
    else:
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file and "vector_store" not in st.session_state:
            with st.spinner("Analyzing PDF..."):
                st.session_state.vector_store = process_pdf(uploaded_file)
            st.success("Analysis complete!")

        # Display history
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Ask a question..."):
            st.session_state.usage_count += 1
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            context = ""
            if "vector_store" in st.session_state:
                docs = st.session_state.vector_store.similarity_search(prompt, k=3)
                context = "\n".join([d.page_content for d in docs])
            
            response = call_ai(f"Context: {context}\n\nQuestion: {prompt}")
            with st.chat_message("assistant"): st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# --- PAGE: QUIZ ---
elif menu == "📝 Quiz Mode":
    st.header("📝 Smart Quiz System")
    tab1, tab2 = st.tabs(["📚 Subject Quiz", "📖 PDF-Based Quiz"])
    
    with tab1:
        subj = st.selectbox("Select Subject", [
            "English", "Maths", "Social Science", "Science", 
            "Tamil", "Hindi", "Malayalam", "Telugu", 
            "Kannada", "Marathi"
        ])
        diff = st.select_slider("Select Difficulty", options=["Easy", "Hard", "Impossible"])
        count = st.number_input("Number of Questions", 1, 20, 5)
        
        if st.button("Generate Subject Quiz", use_container_width=True):
            with st.spinner(f"Preparing {subj} questions..."):
                quiz = call_ai(f"Generate a {diff} difficulty quiz for {subj} with {count} questions. Include answers at the end.")
                st.markdown(quiz)

    with tab2:
        if "vector_store" not in st.session_state:
            st.info("Upload a PDF in the Chat section to generate custom quizzes.")
        else:
            q_num = st.number_input("Questions from Notes", 1, 15, 5)
            if st.button("Generate Quiz from Notes", use_container_width=True):
                docs = st.session_state.vector_store.similarity_search("key summary", k=5)
                context = "\n".join([d.page_content for d in docs])
                res = call_ai(f"Based on this context: {context}\n\nGenerate {q_num} quiz questions.")
                st.markdown(res)

# --- PAGE: STUDY PLAN ---
elif menu == "📅 Study Plan":
    st.header("📅 Daily Study Planner")
    topic = st.text_input("What are you studying for?")
    days = st.slider("Days remaining", 1, 30, 7)
    
    if st.button("Create My Plan", use_container_width=True):
        with st.spinner("Calculating..."):
            plan = call_ai(f"Create a detailed {days}-day study schedule for {topic}. Be practical and organized.")
            st.markdown(plan)
