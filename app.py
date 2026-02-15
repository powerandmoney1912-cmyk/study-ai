import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
import datetime

# --- INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro: Premium", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# FIX: Using the full model path to avoid 404 errors
model = genai.GenerativeModel('models/gemini-1.5-flash')

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- AUTHENTICATION ---
def login_ui():
    st.title("🎓 Study Master Pro: Premium")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

    with tab2:
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Premium Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! You can now Login.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- APP FEATURES ---
def socratic_tutor():
    st.subheader("🧘 Socratic Tutor")
    st.info("I won't give you answers. I will ask questions to help you find them yourself.")
    
    # Persistent History for Socratic Tutor
    if "socratic_history" not in st.session_state:
        st.session_state.socratic_history = []

    for msg in st.session_state.socratic_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("What are you struggling with?"):
        st.session_state.socratic_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        system_prompt = "You are a Socratic Tutor. Never give direct answers. Only ask guiding questions to lead the student to the answer."
        response = model.generate_content(f"{system_prompt}\nStudent: {prompt}")
        
        st.session_state.socratic_history.append({"role": "assistant", "content": response.text})
        with st.chat_message("assistant"): st.write(response.text)
        
        # Save to Supabase History
        supabase.table("history").insert({
            "user_id": st.session_state.user.id,
            "question": prompt,
            "answer": response.text
        }).execute()

def schedule_fixer():
    st.subheader("📅 Reading Schedule Fixer")
    col1, col2 = st.columns(2)
    with col1:
        book = st.text_input("What are you reading?")
        pages = st.number_input("Total Pages", min_value=1)
    with col2:
        days = st.number_input("Days to finish", min_value=1)
        difficulty = st.select_slider("Content Difficulty", options=["Easy", "Medium", "Hard"])

    if st.button("Generate My Schedule"):
        prompt = f"Create a daily reading schedule for a {difficulty} book called '{book}' with {pages} pages to be finished in {days} days. Break it down day by day."
        response = model.generate_content(prompt)
        st.write(response.text)

def quiz_generator():
    st.subheader("📝 Premium Quiz Generator")
    topic = st.text_input("Quiz Topic")
    num_q = st.slider("Number of Questions", 1, 10, 5)
    
    if st.button("Generate Quiz"):
        prompt = f"Generate a {num_q} question multiple choice quiz about {topic}. Provide the questions first, then the answer key at the very bottom."
        response = model.generate_content(prompt)
        st.markdown(response.text)

# --- MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title(f"Welcome!")
    menu = st.sidebar.radio("Go to:", ["Socratic Tutor", "Schedule Fixer", "Quiz Generator"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if menu == "Socratic Tutor": socratic_tutor()
    elif menu == "Schedule Fixer": schedule_fixer()
    elif menu == "Quiz Generator": quiz_generator()
else:
    login_ui()
