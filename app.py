import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro: Premium", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# BUG FIX: Using 'gemini-1.5-flash' with the 'models/' prefix is the most 
# stable way to prevent the 404 error.
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None

# --- 3. AUTHENTICATION UI ---
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
        st.info("Already signed up? Use the Login tab.")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Create Premium Account"):
            try:
                supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Now go to the 'Login' tab.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- 4. PREMIUM FEATURES ---

def chat_interface(mode="normal"):
    """Normal Chat and Socratic Tutor with History"""
    if mode == "socratic":
        st.subheader("🧘 Socratic Tutor (Premium)")
        st.caption("I guide you with questions instead of giving answers.")
        sys_prompt = "You are a Socratic Tutor. Never give a direct answer. Only ask guiding questions."
    else:
        st.subheader("💬 Normal AI Chat (Premium)")
        st.caption("Direct answers and explanations for your study topics.")
        sys_prompt = "You are a helpful, direct AI study assistant."

    if f"history_{mode}" not in st.session_state:
        st.session_state[f"history_{mode}"] = []

    for msg in st.session_state[f"history_{mode}"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask anything..."):
        st.session_state[f"history_{mode}"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.write(prompt)
        
        try:
            response = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
            st.session_state[f"history_{mode}"].append({"role": "assistant", "content": response.text})
            with st.chat_message("assistant"): st.write(response.text)
            
            # Save to Supabase History Table
            supabase.table("history").insert({
                "user_id": st.session_state.user.id,
                "question": prompt,
                "answer": response.text
            }).execute()
        except Exception as e:
            st.error(f"AI Error: {e}")

def schedule_fixer():
    st.subheader("📅 Premium Schedule Fixer")
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Book or Topic")
        volume = st.number_input("Pages/Chapters", min_value=1)
    with col2:
        days = st.number_input("Days to Finish", min_value=1)
        intensity = st.select_slider("Intensity", options=["Light", "Standard", "Hardcore"])

    if st.button("Create My Plan"):
        prompt = f"Create a daily reading schedule for {topic} ({volume} units) over {days} days at {intensity} intensity."
        try:
            response = model.generate_content(prompt)
            st.write(response.text)
        except Exception as e:
            st.error(f"Could not generate schedule: {e}")

# --- 5. MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title("💎 PREMIUM MENU")
    menu = st.sidebar.radio("Select Feature:", 
                            ["Normal Chat", "Socratic Tutor", "Schedule Fixer"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Load selected feature
    if menu == "Normal Chat":
        chat_interface(mode="normal")
    elif menu == "Socratic Tutor":
        chat_interface(mode="socratic")
    elif menu == "Schedule Fixer":
        schedule_fixer()
else:
    login_ui()
