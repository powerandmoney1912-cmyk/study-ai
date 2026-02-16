import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import time

# --- 1. INITIAL SETUP ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    # Use your Supabase URL and ANON KEY from secrets
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Setup Error: Check your Secrets!")
    st.stop()

# --- 2. AUTHENTICATION SYSTEM ---
def login_ui():
    st.title("🔐 Study Master Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e: st.error(f"Login Failed: {e}")
        
        st.divider()
        if st.button("🌐 Sign in with Google (Demo Mode)"):
            st.info("To enable real Google Sign-in, configure 'Auth Providers' in Supabase Dashboard.")

    with tab2:
        new_email = st.text_input("New Email")
        new_pass = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_pass})
                st.success("Account created! Check your email for verification.")
            except Exception as e: st.error(f"Sign Up Failed: {e}")

# --- 3. MAIN APP LOGIC ---
if "user" not in st.session_state:
    login_ui()
else:
    # --- LOAD CHAT HISTORY FROM DATABASE ---
    if "messages" not in st.session_state:
        res = supabase.table("history").select("*").eq("user_id", st.session_state.user.id).order("created_at").execute()
        st.session_state.messages = [{"role": r["role"], "content": r["content"]} for r in res.data]

    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"Logged in as: **{st.session_state.user.email}**")
        if st.button("🚪 Logout"):
            supabase.auth.sign_out()
            del st.session_state.user
            st.rerun()
        
        st.divider()
        menu = st.radio("Navigation", ["💬 Chat History", "👨‍🏫 Teacher Mode", "📝 Notes Maker", "📊 Dashboard"])
        lang = st.selectbox("Language", ["English", "Tamil (தமிழ்)"])

    # AI HELPER
    def ask_ai(prompt, system="Expert Tutor"):
        t_lang = "Tamil" if "Tamil" in lang else "English"
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": f"{system}. Respond in {t_lang}"}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content

    # --- 4. FEATURE MODULES ---
    if menu == "💬 Chat History":
        st.header("Your Chat History")
        # Display existing messages
        for m in st.session_state.messages:
            with st.chat_message(m["role"]): st.write(m["content"])
        
        if p := st.chat_input("Ask a study question..."):
            with st.chat_message("user"): st.write(p)
            ans = ask_ai(p)
            with st.chat_message("assistant"): st.write(ans)
            
            # Save to Database
            supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "user", "content": p}).execute()
            supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "assistant", "content": ans}).execute()
            st.session_state.messages.append({"role": "user", "content": p})
            st.session_state.messages.append({"role": "assistant", "content": ans})

    elif menu == "👨‍🏫 Teacher Mode":
        st.header("👨‍🏫 Teacher Assessment")
        topic = st.text_input("Test Topic")
        if st.button("Generate Test"):
            test_q = ask_ai(f"Give 3 questions about {topic}")
            st.info(test_q)
            # Store in DB so it doesn't vanish
            supabase.table("history").insert({"user_id": st.session_state.user.id, "role": "teacher", "content": f"Topic: {topic}"}).execute()

    elif menu == "📊 Dashboard":
        st.header("Your Study Stats")
        res = supabase.table("history").select("*", count="exact").eq("user_id", st.session_state.user.id).execute()
        st.metric("Total Interactions", res.count)
