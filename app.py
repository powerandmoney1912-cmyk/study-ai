import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import pandas as pd

# --- 1. CONFIG & THEMES ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

if "zen_mode" not in st.session_state: st.session_state.zen_mode = False

# --- 2. AUTH & CLIENTS ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing API Keys in Secrets!")
    st.stop()

# --- 3. SESSION STATE ---
states = {
    "messages": [], 
    "user_uuid": str(uuid.uuid4()), 
    "is_premium": False, 
    "test_q": None, 
    "lang": "English", 
    "timer_active": False,
    "timer_end": None
}
for key, val in states.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 4. HELPERS ---
def get_usage():
    try:
        limit_time = (datetime.now() - timedelta(hours=24)).isoformat()
        res = supabase.table("history").select("id", count="exact").eq("user_id", st.session_state.user_uuid).gte("created_at", limit_time).execute()
        return res.count if res.count else 0
    except: return 0

def save_db(role, content, itype="text", score=0):
    try: supabase.table("history").insert({"user_id": st.session_state.user_uuid, "role": role, "content": str(content), "interaction_type": itype, "score": score}).execute()
    except: pass

# --- 5. SIDEBAR (TIMER & SIGNATURE) ---
if not st.session_state.zen_mode:
    with st.sidebar:
        st.title("🎓 Study Master Pro")
        st.session_state.lang = st.selectbox("🌍 Language", ["English", "Hindi", "Spanish", "French"])
        
        # CUSTOM FOCUS TIMER
        st.divider()
        st.subheader("⏱️ Custom Focus Timer")
        
        if not st.session_state.timer_active:
            # User chooses custom minutes
            custom_mins = st.number_input("Set Minutes", min_value=1, max_value=180, value=25)
            if st.button("🚀 Start Focus", use_container_width=True):
                st.session_state.timer_active = True
                st.session_state.timer_end = datetime.now() + timedelta(minutes=custom_mins)
                st.rerun()
        else:
            # Timer is running
            rem = st.session_state.timer_end - datetime.now()
            if rem.total_seconds() > 0:
                st.warning(f"Focusing: {str(rem).split('.')[0]}")
                if st.button("🛑 Stop Timer", use_container_width=True):
                    st.session_state.timer_active = False
                    st.session_state.timer_end = None
                    st.error("Focus Session Stopped")
                    st.rerun()
            else:
                st.balloons()
                st.success("Session Complete! 🎉")
                st.session_state.timer_active = False
                st.session_state.timer_end = None

        # Usage Meter
        st.divider()
        usage = get_usage()
        limit = 250 if st.session_state.is_premium else 50
        st.metric("Daily Usage", f"{usage}/{limit}")
        
        # Signature
        st.divider()
        st.write("✨ **Made by Aarya**")
        st.write("❤️ *Made with love*")
        if st.button("Toggle Zen Mode"):
            st.session_state.zen_mode = True
            st.rerun()

# --- 6. MAIN CONTENT ---
if st.session_state.zen_mode:
    if st.button("⬅️ Exit Zen Mode"):
        st.session_state.zen_mode = False
        st.rerun()

menu = st.tabs(["💬 Chat", "👨‍🏫 Teacher", "📝 Flashcards", "📊 Dashboard", "📅 Scheduler"])

def ask_ai(prompt, sys="Study Tutor"):
    full_sys = f"{sys}. Respond in {st.session_state.lang}."
    resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}])
    return resp.choices[0].message.content

# 💬 CHAT MODULE
with menu[0]:
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask anything..."):
        st.session_state.messages.append({"role": "user", "content": p})
        with st.chat_message("user"): st.write(p)
        ans = ask_ai(p)
        with st.chat_message("assistant"): st.write(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        save_db("user", p); save_db("assistant", ans)

# 👨‍🏫 TEACHER MODE
with menu[1]:
    topic = st.text_input("Test Topic")
    if st.button("Get Test"):
        st.session_state.test_q = ask_ai(f"5 questions about {topic}. No answers.")
    if st.session_state.test_q:
        st.info(st.session_state.test_q)
        u_ans = st.text_area("Answers")
        if st.button("Submit"):
            res = ask_ai(f"Grade these. Score /10. Questions: {st.session_state.test_q}. Answers: {u_ans}")
            st.success(res)

# 📊 DASHBOARD
with menu[3]:
    st.subheader("📈 Performance Analysis")
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user_uuid).execute()
    if hist.data:
        df = pd.DataFrame(hist.data)
        st.line_chart(df[df['score'] > 0]['score'])
