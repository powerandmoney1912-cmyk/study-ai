import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Check your Secrets! API Keys are missing.")
    st.stop()

# --- 2. SESSION STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "timer_active" not in st.session_state: st.session_state.timer_active = False
if "timer_end" not in st.session_state: st.session_state.timer_end = None

# --- 3. SIDEBAR (TIMER & TAMIL) ---
with st.sidebar:
    st.title("🎓 Study Master Pro")
    
    # TAMIL ADDED HERE
    lang = st.selectbox("🌍 Study Language", ["English", "Tamil (தமிழ்)", "Hindi", "Spanish", "French"])
    
    st.divider()
    st.subheader("⏱️ Custom Focus Timer")
    
    if not st.session_state.timer_active:
        mins = st.number_input("Set Minutes", 1, 180, 25)
        if st.button("🚀 Start Focus", use_container_width=True):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()
    else:
        # THE TIMER COUNTDOWN FIX
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing... {str(rem).split('.')[0]}")
            if st.button("🛑 Stop Timer", use_container_width=True):
                st.session_state.timer_active = False
                st.session_state.timer_end = None
                st.rerun()
            # This makes the app refresh to show the countdown
            time.sleep(1)
            st.rerun()
        else:
            st.balloons()
            st.success("Session Done! 🎉")
            st.session_state.timer_active = False

    st.divider()
    st.write("✨ **Made by Aarya**")
    st.write("❤️ *Made with love*")

# --- 4. AI ENGINE ---
def ask_ai(prompt, system="Expert Study Tutor"):
    # Force AI to use selected language
    target_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. You MUST respond ONLY in {target_lang}."
    
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"

# --- 5. MAIN CONTENT ---
tabs = st.tabs(["💬 Chat", "👨‍🏫 Teacher Mode"])

with tabs[0]:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
        
    if p := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})

with tabs[1]:
    st.header("👨‍🏫 Teacher Assessment")
    topic = st.text_input("Enter topic for test:")
    if st.button("Generate Test"):
        test = ask_ai(f"Give 5 questions about {topic}. No answers.")
        st.session_state.active_test = test
        
    if "active_test" in st.session_state:
        st.info(st.session_state.active_test)
        u_ans = st.text_area("Your Answers:")
        if st.button("Submit & Grade"):
            grade = ask_ai(f"Grade these. Score /10. Test: {st.session_state.active_test}. Answers: {u_ans}")
            st.success(grade)
