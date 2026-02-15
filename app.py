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
MODEL_NAME = 'models/gemini-1.5-flash'
model = genai.GenerativeModel(MODEL_NAME)

# --- 2. SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
# This ensures premium is False by default when you first open the app
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False

# --- 3. HELPER FUNCTIONS ---
def get_chat_count():
    try:
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user.id).execute()
        return res.count if res.count else 0
    except:
        return 0

# --- 4. MAIN APP ---
if st.session_state.user:
    st.sidebar.title("💎 Study Master Pro")
    
    # --- REDEMPTION SECTION (The Fix) ---
    if not st.session_state.is_premium:
        st.sidebar.warning("Standard Account: 10 Chat Limit")
        with st.sidebar.expander("🔑 ENTER PREMIUM CODE"):
            code_input = st.text_input("Redemption Code", type="password")
            if st.button("Unlock 250 Chats"):
                if code_input == "STUDY777":
                    st.session_state.is_premium = True
                    st.sidebar.success("Premium Unlocked!")
                    st.rerun()
                else:
                    st.sidebar.error("Invalid Code")
    else:
        st.sidebar.success("✅ Premium Active: 250 Chats")

    # --- CHAT LIMIT LOGIC ---
    current_chats = get_chat_count()
    limit = 250 if st.session_state.is_premium else 10
    
    st.sidebar.divider()
    st.sidebar.write(f"**Usage:** {current_chats} / {limit} chats")
    
    # Navigation
    menu = st.sidebar.radio("Features", ["Normal Chat", "Socratic Tutor", "Schedule Fixer"])
    
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.is_premium = False
        st.rerun()

    # --- FEATURE TABS ---
    if current_chats >= limit:
        st.error(f"🛑 Limit Reached ({current_chats}/{limit}). Enter a Premium code in the sidebar to continue to 250!")
    else:
        # Chat Logic
        if menu == "Normal Chat":
            st.subheader("💬 Normal Chat")
            prompt = st.chat_input("Ask me anything...")
            if prompt:
                # Save to Supabase and Generate AI response here...
                pass 
        # (Add Socratic Tutor and Schedule Fixer logic here)

else:
    # Login UI logic...
    st.title("Please Login")
    # ... (rest of your login code)
