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

# 404 BUG FIX: Explicit model path
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. LOGIC: CHAT LIMITS & 24HR RESET ---
def get_daily_chat_count():
    """Counts messages sent in the last 24 hours"""
    try:
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history")\
            .select("id", count="exact")\
            .eq("user_id", st.session_state.user.id)\
            .gte("created_at", yesterday)\
            .execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. FEATURES ---

def quiz_zone():
    st.subheader("📝 Quiz Zone")
    topic = st.text_input("Enter topic for the quiz:")
    difficulty = st.select_slider("Difficulty", options=["Easy", "Medium", "Hard"])
    
    if st.button("Generate Quiz"):
        with st.spinner("Creating your quiz..."):
            prompt = f"Generate a 5-question multiple choice quiz about {topic} at {difficulty} level. Show answers at the end."
            resp = model.generate_content(prompt)
            st.markdown(resp.text)

def file_mode():
    st.subheader("📁 File Mode (PDF/Images)")
    st.info("Upload a study material to get detailed notes.")
    uploaded_file = st.file_uploader("Upload Image or PDF", type=["png", "jpg", "jpeg", "pdf"])
    
    if uploaded_file is not None:
        if st.button("Generate Notes"):
            with st.spinner("Analyzing..."):
                if uploaded_file.type.startswith("image"):
                    img = PIL.Image.open(uploaded_file)
                    resp = model.generate_content(["Provide detailed study notes based on this image content.", img])
                else:
                    # Basic PDF text processing (simplified for this version)
                    resp = model.generate_content(f"Analyze this document and provide a summary: {uploaded_file.name}")
                
                st.write(resp.text)

def chat_logic(mode="normal"):
    # Limit Check
    count = get_daily_chat_count()
    limit = 250 if st.session_state.is_premium else 50
    
    st.sidebar.metric("24h Usage", f"{count} / {limit}")
    
    if count >= limit:
        st.error(f"Daily limit reached! ({count}/{limit}). Reset in 24h or use Premium code.")
        return

    prompt = st.chat_input("Ask anything...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        sys_prompt = "Socratic Tutor: ask questions only." if mode == "socratic" else "Helpful assistant."
        resp = model.generate_content(f"{sys_prompt}\nUser: {prompt}")
        with st.chat_message("assistant"): st.write(resp.text)
        
        # Save to DB
        supabase.table("history").insert({
            "user_id": st.session_state.user.id, 
            "question": prompt, 
            "answer": resp.text
        }).execute()

# --- 5. MAIN UI ---
if st.session_state.user:
    st.sidebar.title("💎 Study Master Pro")
    
    # Redemption Zone
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM CODE"):
            code = st.text_input("Code", type="password")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
    
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode", "Schedule Fixer"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if menu == "Normal Chat": chat_logic("normal")
    elif menu == "Socratic Tutor": chat_logic("socratic")
    elif menu == "Quiz Zone": quiz_zone()
    elif menu == "File Mode": file_mode()
    elif menu == "Schedule Fixer":
        # (Existing schedule fixer code here)
        st.write("Schedule Fixer Active")
else:
    # (Existing login_ui code here)
    st.title("Please Login")
    if st.button("Go to Login"): st.rerun()
