import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# --- INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro: Premium", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# FIX: Using 'gemini-1.5-flash-latest' to ensure the model is found
MODEL_NAME = 'gemini-1.5-flash-latest'
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
                st.error(f"Login failed: {e}")

    with tab2:
        st.info("Already signed up? Use the Login tab instead.")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Premium Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Now go to the 'Login' tab.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- APP FEATURES ---

def chat_interface(mode="normal"):
    """Combined Normal Chat and Socratic Tutor with History"""
    if mode == "socratic":
        st.subheader("🧘 Socratic Tutor")
        st.caption("I help you find answers by asking the right questions.")
        sys_prompt = "You are a Socratic Tutor. Never give a direct answer. Respond only with questions that guide the student."
    else:
        st.subheader("💬 Normal AI Chat")
        st.caption("Direct answers and explanations for your study topics.")
        sys_prompt = "You are a helpful, direct AI study assistant."

    if f"chat_history_{mode}" not in st.session_state:
        st.session_state[f"chat_history_{mode}"] = []

    # Display Chat History
    for msg in st.session_state[f"chat_history_{mode}"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask your study question..."):
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
        topic = st.text_input("What are you studying?")
        volume = st.number_input("Total Pages/Chapters", min_value=1)
    with col2:
        days = st.number_input("Days to complete", min_value=1)
        intensity = st.select_slider("Intensity", options=["Casual", "Steady", "Exam Mode"])

    if st.button("Generate My Schedule"):
        with st.spinner("Building your plan..."):
            prompt = f"Create a daily study schedule for {topic}. Volume: {volume} units. Time: {days} days. Intensity: {intensity}."
            response = model.generate_content(prompt)
            st.write(response.text)

def quiz_generator():
    st.subheader("📝 Premium Quiz Generator")
    topic = st.text_input("Quiz Topic")
    num_q = st.slider("Questions", 3, 10, 5)
    
    if st.button("Generate Quiz"):
        prompt = f"Create a {num_q} question multiple choice quiz about {topic}. Provide answers at the end."
        response = model.generate_content(prompt)
        st.markdown(response.text)

# --- MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title("Premium Navigation")
    menu = st.sidebar.radio("Go to:", ["Normal Chat", "Socratic Tutor", "Schedule Fixer", "Quiz Generator"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if menu == "Normal Chat": chat_interface(mode="normal")
    elif menu == "Socratic Tutor": chat_interface(mode="socratic")
    elif menu == "Schedule Fixer": schedule_fixer()
    elif menu == "Quiz Generator": quiz_generator()
else:
    login_ui()
