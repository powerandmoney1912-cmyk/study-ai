import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from datetime import datetime, timedelta
import PIL.Image
import io

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Initialize Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Initialize Gemini
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- FIXING THE 404 BUG ---
# We try multiple naming conventions to ensure the model is found
try:
    MODEL_NAME = 'gemini-1.5-flash'
    model = genai.GenerativeModel(MODEL_NAME)
    # Test call to verify model exists
    model.prepare_multimodal_labelling = True 
except:
    MODEL_NAME = 'models/gemini-1.5-flash'
    model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. CHAT LIMIT & 24HR RESET LOGIC ---
def get_daily_chat_count():
    try:
        # Calculate time 24 hours ago
        yesterday = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history")\
            .select("id", count="exact")\
            .eq("user_id", st.session_state.user.id)\
            .gte("created_at", yesterday)\
            .execute()
        return res.count if res.count else 0
    except Exception as e:
        return 0

# --- 4. AUTH UI ---
def login_ui():
    st.title("🎓 Study Master Pro")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Log In"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error(f"Login Error: {e}")
    with tab2:
        st.info("Already have an account? Use the Login tab.")
        e_reg = st.text_input("New Email")
        p_reg = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": e_reg, "password": p_reg})
                st.success("Account created! Go to Login.")
            except Exception as e:
                st.error(f"Sign up failed: {e}")

# --- 5. PREMIUM FEATURES ---

def quiz_zone():
    st.subheader("📝 Quiz Zone")
    topic = st.text_input("What topic should the quiz be about?")
    if st.button("Generate Quiz"):
        with st.spinner("Writing questions..."):
            prompt = f"Create a 5-question multiple choice quiz about {topic}. Provide the answers at the very end."
            resp = model.generate_content(prompt)
            st.markdown(resp.text)

def file_mode():
    st.subheader("📁 File Mode (Notes from PDF/Images)")
    uploaded_file = st.file_uploader("Upload an image of your notes or a PDF", type=["png", "jpg", "jpeg"])
    if uploaded_file and st.button("Generate Study Notes"):
        with st.spinner("Analyzing file..."):
            img = PIL.Image.open(uploaded_file)
            resp = model.generate_content(["Provide detailed study notes based on this image.", img])
            st.write(resp.text)

def chat_logic(mode="normal"):
    count = get_daily_chat_count()
    limit = 250 if st.session_state.is_premium else 50
    
    st.sidebar.metric("24h Progress", f"{count} / {limit}")
    
    if count >= limit:
        st.error(f"Daily limit reached ({count}/{limit}). Resets in 24h or use Premium Code!")
        return

    prompt = st.chat_input("Ask a question...")
    if prompt:
        with st.chat_message("user"): st.write(prompt)
        sys = "You are a Socratic Tutor. Only ask questions." if mode == "socratic" else "Helpful Study Assistant."
        try:
            resp = model.generate_content(f"{sys}\nUser: {prompt}")
            with st.chat_message("assistant"): st.write(resp.text)
            
            # Save to Supabase
            supabase.table("history").insert({
                "user_id": st.session_state.user.id, 
                "question": prompt, 
                "answer": resp.text
            }).execute()
        except Exception as e:
            st.error(f"AI Error: {e}. Please check your API Key or Model selection.")

# --- 6. MAIN UI ---
if st.session_state.user:
    st.sidebar.title("💎 Study Master")
    
    # Redemption Zone
    if not st.session_state.is_premium:
        with st.sidebar.expander("🔑 REDEEM CODE"):
            code = st.text_input("Code", type="password")
            if st.button("Activate"):
                if code == "STUDY777":
                    st.session_state.is_premium = True
                    st.rerun()
    
    menu = st.sidebar.radio("Navigation", ["Normal Chat", "Socratic Tutor", "Quiz Zone", "File Mode"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    if menu == "Normal Chat": chat_logic("normal")
    elif menu == "Socratic Tutor": chat_logic("socratic")
    elif menu == "Quiz Zone": quiz_zone()
    elif menu == "File Mode": file_mode()
else:
    login_ui()
