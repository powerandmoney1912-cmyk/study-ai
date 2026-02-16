import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# --- 1. CORE SETUP ---
st.set_page_config(page_title="Study Master Infinity", layout="wide")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing in Secrets!")
    st.stop()

# --- 2. AUTH & USERNAME (Fixes APIError) ---
if "user" not in st.session_state:
    st.title("🛡️ Secure Study Login")
    t1, t2 = st.tabs(["Login", "Sign Up"])
    with t1:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Log In"):
            res = supabase.auth.sign_in_with_password({"email": e, "password": p})
            st.session_state.user = res.user
            st.rerun()
    with t2:
        ne = st.text_input("New Email")
        np = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            supabase.auth.sign_up({"email": ne, "password": np})
            st.success("Verify your email!")
    st.stop()

# Check Profile
profile_res = supabase.table("profiles").select("*").eq("id", st.session_state.user.id).execute()
if not profile_res.data:
    st.title("👋 Name your AI Assistant")
    u_name = st.text_input("Username")
    if st.button("Save Profile"):
        supabase.table("profiles").insert({"id": st.session_state.user.id, "username": u_name}).execute()
        st.rerun()
    st.stop()

user_data = profile_res.data[0]

# --- 3. SIDEBAR (Premium + Features) ---
with st.sidebar:
    st.title(f"👤 {user_data.get('username', 'User')}")
    st.write(f"Level: {user_data.get('xp', 0)//100 + 1}")
    
    # Premium Code
    if not user_data.get('is_premium'):
        p_code = st.text_input("🎟️ Premium Code", type="password")
        if st.button("Activate"):
            if p_code == "STUDY777":
                supabase.table("profiles").update({"is_premium": True}).eq("id", st.session_state.user.id).execute()
                st.success("💎 Premium Unlocked!"); time.sleep(1); st.rerun()
    else: st.success("💎 PREMIUM ACTIVE")

    menu = st.radio("Features", ["💬 Chat Memory", "📅 Schedule Gen", "👨‍🏫 Teacher Mode", "📝 Notes Maker", "🗂️ Flashcards", "📸 Visual Lab", "📊 Dashboard"])
    lang = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])
    st.divider()
    st.write("✨ **Made by Aarya**")
    if st.button("Logout"):
        supabase.auth.sign_out()
        del st.session_state.user; st.rerun()

# --- 4. THE MEMORY ENGINE (Improves AI Memory) ---
def ask_ai(prompt, system="Expert Tutor"):
    # We fetch the last 10 messages to give the AI "Memory"
    past_chats = supabase.table("history").select("role, content").eq("user_id", st.session_state.user.id).order("created_at", desc=True).limit(10).execute()
    
    memory_context = ""
    for chat in reversed(past_chats.data):
        memory_context += f"{chat['role']}: {chat['content']}\n"

    t_lang = "Tamil" if "Tamil" in lang else "English"
    full_sys = f"{system}. Respond in {t_lang}. Use this past memory to stay consistent: {memory_context}"
    
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. MODULES ---

if menu == "💬 Chat Memory":
    st.header("Unlimited Chat Memory")
    # Fix KeyError using .get()
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
    for m in hist.data:
        with st.chat_message(m.get("role", "assistant")): st.write(m.get("content", ""))
    
    if p := st.chat_input("Ask anything..."):
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
        supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()

elif menu == "📅 Schedule Gen":
    st.header("📅 AI Schedule Generator")
    tasks = st.text_area("What subjects do you need to cover?")
    if st.button("Generate Plan"):
        st.markdown(ask_ai(f"Create a strict 7-day study schedule for: {tasks}"))

elif menu == "📸 Visual Lab":
    st.header("Visual Lab")
    img = st.camera_input("Snapshot")
    if img and st.button("Analyze"):
        st.write(ask_ai("Analyze this study image content."))
# ... (Other modules remain same as per previous clean version)
