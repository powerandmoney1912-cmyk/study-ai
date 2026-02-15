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

# 404 BUG FIX: Use the full model path
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. HELPER FUNCTIONS ---

def get_chat_count():
    """Fetch total messages sent by this user from Supabase"""
    try:
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. AUTHENTICATION UI ---
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

# --- 5. CHAT LOGIC WITH LIMITS ---

def chat_interface(mode="socratic"):
    current_chats = get_chat_count()
    limit = 250 if st.session_state.is_premium else 10  # Free limit set to 10 for testing
    
    st.sidebar.metric("Chats Used", f"{current_chats}/{limit}")

    if mode == "socratic":
        st.subheader("🧘 Socratic Tutor")
        sys_prompt = "You are a Socratic Tutor. Never give a direct answer. Only ask questions."
    else:
        st.subheader("💬 Normal AI Chat")
        sys_prompt = "You are a helpful AI study assistant."

    if f"hist_{mode}" not in st.session_state:
        st.session_state[f"hist_{mode}"] = []

    for msg in st.session_state[f"hist_{mode}"]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if current_chats >= limit:
        st.error(f"Limit Reached! {limit}/{limit} chats used. Redeem Premium to get 250 chats.")
    else:
        if prompt := st.chat_input("Ask a question..."):
            st.session_state[f"hist_{mode}"].append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.write(prompt)
            
            try:
                response = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
                st.session_state[f"hist_{mode}"].append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant"): st.write(response.text)
                
                # SAVE TO SUPABASE TO TRACK LIMIT
                supabase.table("history").insert({
                    "user_id": st.session_state.user.id,
                    "question": prompt,
                    "answer": response.text
                }).execute()
                st.rerun() # Refresh counter
            except Exception as e:
                st.error(f"AI Error: {e}")

def schedule_fixer():
    st.subheader("📅 Schedule Fixer")
    topic = st.text_input("What are you studying?")
    days = st.number_input("Days", min_value=1)
    if st.button("Generate Plan"):
        response = model.generate_content(f"Plan for {topic} over {days} days.")
        st.write(response.text)

# --- 6. MAIN NAVIGATION ---
if st.session_state.user:
    st.sidebar.title("Study Master")
    
    # PREMIUM REDEMPTION
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 Redeem Premium"):
            code = st.text_input("Enter Special Code")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium Activated! Limit is now 250.")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("💎 Premium: 250 Chat Limit")

    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Schedule Fixer"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

    if menu == "Normal Chat": chat_interface(mode="normal")
    elif menu == "Socratic Tutor": chat_interface(mode="socratic")
    elif menu == "Schedule Fixer": schedule_fixer()
else:
    login_ui()
