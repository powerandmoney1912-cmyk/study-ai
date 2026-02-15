import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# 404 BUG FIX: Using the full model path
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. AUTHENTICATION UI ---
def login_ui():
    st.title("🎓 Study Master Pro")
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
        st.info("Already signed up? Use the Login tab.")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Success! Now go to the 'Login' tab.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- 4. FEATURES ---

def chat_interface(mode="socratic"):
    if mode == "socratic":
        st.subheader("🧘 Socratic Tutor")
        sys_prompt = "You are a Socratic Tutor. Never give a direct answer. Only ask questions."
    else:
        st.subheader("💬 Normal AI Chat (Premium)")
        sys_prompt = "You are a helpful AI study assistant."

    if f"hist_{mode}" not in st.session_state:
        st.session_state[f"hist_{mode}"] = []

    for msg in st.session_state[f"hist_{mode}"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state[f"hist_{mode}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        try:
            response = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
            st.session_state[f"hist_{mode}"].append({"role": "assistant", "content": response.text})
            with st.chat_message("assistant"): st.write(response.text)
        except Exception as e:
            st.error(f"AI Error: {e}")

def schedule_fixer():
    st.subheader("📅 Schedule Fixer (Premium)")
    topic = st.text_input("What are you studying?")
    days = st.number_input("Days", min_value=1)
    if st.button("Generate Plan"):
        response = model.generate_content(f"Plan for {topic} over {days} days.")
        st.write(response.text)

# --- 5. MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title("Study Master")
    
    # PREMIUM REDEMPTION OPTION
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 Redeem Premium"):
            code = st.text_input("Enter Special Code")
            if st.button("Activate"):
                if code == "STUDY777": # <-- CHANGE YOUR CODE HERE
                    st.session_state.is_premium = True
                    st.success("Premium Activated!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("💎 Premium Active")

    # Menu options change based on Premium status
    options = ["Socratic Tutor"]
    if st.session_state.is_premium:
        options += ["Normal Chat", "Schedule Fixer"]
    
    menu = st.sidebar.radio("Navigation", options)
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

    if menu == "Socratic Tutor": chat_interface(mode="socratic")
    elif menu == "Normal Chat": chat_interface(mode="normal")
    elif menu == "Schedule Fixer": schedule_fixer()
else:
    login_ui()
