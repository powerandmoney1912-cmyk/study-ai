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

# FIX: Using 'gemini-1.5-flash' without prefixes often resolves 404 version errors
# If this fails, change it to 'models/gemini-1.5-flash'
MODEL_NAME = 'gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- AUTHENTICATION ---
def login_ui():
    st.title("🎓 Study Master Pro: Premium Edition")
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
                st.error(f"Login failed: Your account exists but authentication failed. {e}")

    with tab2:
        st.info("If you get a 'duplicate key' error, it means you are already signed up! Just click the Login tab.")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Premium Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Success! Now go to the 'Login' tab to enter.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- APP FEATURES ---

def chat_interface(mode="normal"):
    """Combined Normal Chat and Socratic Tutor"""
    if mode == "socratic":
        st.subheader("🧘 Socratic Tutor")
        st.caption("I help you find answers by asking the right questions.")
        sys_prompt = "You are a Socratic Tutor. Never give a direct answer. Respond only with questions that guide the student."
    else:
        st.subheader("💬 Normal AI Chat")
        st.caption("Standard AI assistant for quick help and explanations.")
        sys_prompt = "You are a helpful, direct AI study assistant."

    if f"chat_history_{mode}" not in st.session_state:
        st.session_state[f"chat_history_{mode}"] = []

    for msg in st.session_state[f"chat_history_{mode}"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("How can I help you study?"):
        st.session_state[f"chat_history_{mode}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        try:
            full_prompt = f"{sys_prompt}\nUser: {prompt}"
            response = model.generate_content(full_prompt)
            
            st.session_state[f"chat_history_{mode}"].append({"role": "assistant", "content": response.text})
            with st.chat_message("assistant"): st.write(response.text)
            
            # Save to Supabase
            supabase.table("history").insert({
                "user_id": st.session_state.user.id,
                "question": prompt,
                "answer": response.text
            }).execute()
        except Exception as e:
            st.error(f"AI Error: {e}")

def schedule_fixer():
    st.subheader("📅 Reading Schedule Fixer")
    col1, col2 = st.columns(2)
    with col1:
        book = st.text_input("Topic or Book Name")
        pages = st.number_input("Total Pages/Chapters", min_value=1)
    with col2:
        days = st.number_input("Days available", min_value=1)
        intensity = st.select_slider("Study Intensity", options=["Light", "Moderate", "Exam Prep"])

    if st.button("Generate Schedule"):
        with st.spinner("Calculating..."):
            prompt = f"Create a daily study/reading schedule for {book}. Total volume: {pages} units. Time: {days} days. Intensity: {intensity}."
            response = model.generate_content(prompt)
            st.write(response.text)

def quiz_generator():
    st.subheader("📝 Premium Quiz Builder")
    topic = st.text_input("What is the quiz about?")
    q_count = st.slider("Questions", 3, 10, 5)
    
    if st.button("Build Quiz"):
        prompt = f"Create a {q_count} question multiple choice quiz on {topic}. Provide answers at the end."
        response = model.generate_content(prompt)
        st.markdown(response.text)

# --- MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title("Premium Navigation")
    menu = st.sidebar.radio("Features:", ["Normal Chat", "Socratic Tutor", "Schedule Fixer", "Quiz Builder"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if menu == "Normal Chat": chat_interface(mode="normal")
    elif menu == "Socratic Tutor": chat_interface(mode="socratic")
    elif menu == "Schedule Fixer": schedule_fixer()
    elif menu == "Quiz Builder": quiz_generator()
else:
    login_ui()
