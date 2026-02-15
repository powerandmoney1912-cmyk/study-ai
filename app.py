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

# FIX: We use a try-except block to find the brain your API allows
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    # Simple check to see if it works
    test = model.generate_content("hi")
except:
    try:
        model = genai.GenerativeModel('gemini-pro')
    except:
        st.error("🚨 API Key Error: Please check your Google AI Studio key.")

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. LIMIT LOGIC (24HR RESET) ---
def get_daily_chat_count():
    try:
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).gte("created_at", yesterday).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. MAIN FEATURES ---

def chat_logic(mode="normal"):
    count = get_daily_chat_count()
    limit = 250 if st.session_state.is_premium else 50
    st.sidebar.metric("24h Usage", f"{count} / {limit}")

    if count >= limit:
        st.error(f"Daily limit reached! ({count}/{limit}). Resets in 24h or use Premium code.")
        return

    prompt = st.chat_input("Ask a question...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        sys_prompt = "You are a Socratic Tutor. Only ask questions." if mode == "socratic" else "Helpful Study Assistant."
        try:
            resp = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
            with st.chat_message("assistant"): st.write(resp.text)
            # Save to Supabase to track limit
            supabase.table("history").insert({"user_id": st.session_state.user.id, "question": prompt, "answer": resp.text}).execute()
        except Exception as e:
            st.error(f"AI Error: {e}")

# --- 5. UI LAYOUT ---
if st.session_state.user:
    st.sidebar.title("🎓 Study Master Pro")
    
    # REDEMPTION ZONE (Enter code here)
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEMPTION ZONE"):
            code = st.text_input("Enter Special Code", type="password")
            if st.button("Unlock 250 Chats"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.success("Premium Unlocked!")
                    st.rerun()
                else:
                    st.error("Invalid Code")
    else:
        st.sidebar.success("✅ PREMIUM ACTIVE")
    
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode"])
    
    if menu == "Normal Chat": chat_logic("normal")
    elif menu == "Socratic Tutor": chat_logic("socratic")
    elif menu == "Quiz Zone":
        st.subheader("📝 Quiz Zone")
        topic = st.text_input("Enter Topic for Quiz")
        if st.button("Start Quiz"):
            st.write(model.generate_content(f"Create a 5 question quiz on {topic}").text)
    elif menu == "File Mode":
        st.subheader("📁 File Mode")
        up = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
        if up and st.button("Get Notes"):
            img = PIL.Image.open(up)
            st.write(model.generate_content(["Provide detailed study notes based on this image", img]).text)

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()
else:
    # Login Logic
    st.title("Welcome to Study Master Pro")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.rerun()
        except:
            st.error("Login failed. Check your email/password.")
