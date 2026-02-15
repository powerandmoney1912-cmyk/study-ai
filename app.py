import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- THE ULTIMATE 404 BUG FIX ---
def get_working_model():
    # List of possible model name formats
    model_names = ['models/gemini-1.5-flash', 'gemini-1.5-flash', 'models/gemini-pro']
    for name in model_names:
        try:
            m = genai.GenerativeModel(name)
            # Test it with a tiny call
            m.generate_content("test")
            return m, name
        except:
            continue
    return None, None

model, working_name = get_working_model()

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. LIMIT LOGIC ---
def get_daily_chat_count():
    try:
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).gte("created_at", yesterday).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. MAIN FEATURES ---

def chat_logic(mode="normal"):
    if not model:
        st.error("AI Model could not be initialized. Please check your API Key.")
        return

    count = get_daily_chat_count()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{count} / {limit}")

    if count >= limit:
        st.error(f"Limit Reached! Resets in 24h or use Premium code.")
        return

    prompt = st.chat_input("Ask a question...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        sys_prompt = "Socratic Tutor: ask questions only." if mode == "socratic" else "Direct study assistant."
        try:
            resp = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
            with st.chat_message("assistant"): st.write(resp.text)
            supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
        except Exception as e:
            st.error(f"AI Error: {e}")

# --- 5. UI LAYOUT ---
if st.session_state.user:
    st.sidebar.title("🎓 Study Master Pro")
    
    # Redemption Zone
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM PREMIUM"):
            code = st.text_input("Enter Code", type="password")
            if st.button("Unlock 250 Chats"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
    
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode"])
    
    if menu == "Normal Chat": chat_logic("normal")
    elif menu == "Socratic Tutor": chat_logic("socratic")
    elif menu == "Quiz Zone":
        topic = st.text_input("Quiz Topic")
        if st.button("Start Quiz"):
            st.write(model.generate_content(f"Generate a quiz on {topic}").text)
    elif menu == "File Mode":
        up = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
        if up and st.button("Get Notes"):
            img = PIL.Image.open(up)
            st.write(model.generate_content(["Summarize this image into notes", img]).text)

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
else:
    # Basic Login UI
    st.title("Welcome to Study Master Pro")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.rerun()
        except:
            st.error("Login failed.")
