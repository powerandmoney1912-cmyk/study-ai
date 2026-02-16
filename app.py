import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time
import pandas as pd

# --- 1. CONFIG & THEMES ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

# Zen Mode / Theme Logic
if "zen_mode" not in st.session_state: st.session_state.zen_mode = False

if st.session_state.zen_mode:
    st.markdown("""<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} .stSidebar {display: none;}</style>""", unsafe_allow_html=True)

# --- 2. AUTH & CLIENTS ---
try:
    supabase = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Missing API Keys in Secrets!")
    st.stop()

# --- 3. SESSION STATE ---
states = ["messages", "user_uuid", "is_premium", "test_q", "lang", "pomodoro_end"]
for s in states:
    if s not in st.session_state:
        if s == "messages": st.session_state[s] = []
        elif s == "user_uuid": st.session_state[s] = str(uuid.uuid4())
        elif s == "lang": st.session_state[s] = "English"
        else: st.session_state[s] = None

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

def ask_ai(prompt, sys="Study Tutor"):
    usage = get_usage()
    limit = 250 if st.session_state.is_premium else 50
    if usage >= limit: return "LIMIT"
    
    full_sys = f"{sys}. Respond in {st.session_state.lang}."
    try:
        resp = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}])
        return resp.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# --- 5. SIDEBAR ---
if not st.session_state.zen_mode:
    with st.sidebar:
        st.title("🎓 Study Master Pro")
        st.session_state.lang = st.selectbox("🌍 Language", ["English", "Hindi", "Spanish", "French"])
        
        # Pomodoro Timer
        st.divider()
        st.subheader("⏱️ Focus Timer")
        if st.button("Start 25m Focus"):
            st.session_state.pomodoro_end = datetime.now() + timedelta(minutes=25)
        if st.session_state.pomodoro_end and datetime.now() < st.session_state.pomodoro_end:
            rem = st.session_state.pomodoro_end - datetime.now()
            st.warning(f"Focusing! {str(rem).split('.')[0]} left")
        
        # Premium
        st.divider()
        if not st.session_state.is_premium:
            code = st.text_input("Premium Code", type="password")
            if st.button("Redeem") and code == "STUDY777":
                st.session_state.is_premium = True
                st.rerun()
        
        st.metric("Daily Usage", f"{get_usage()}/{250 if st.session_state.is_premium else 50}")
        
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

# CHAT & TRANSLATOR
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

# TEACHER & GRADING
with menu[1]:
    topic = st.text_input("Test Topic")
    if st.button("Generate Test"):
        st.session_state.test_q = ask_ai(f"5 questions about {topic}. No answers.")
    if st.session_state.test_q:
        st.info(st.session_state.test_q)
        u_ans = st.text_area("Your Answers")
        if st.button("Grade"):
            res = ask_ai(f"Grade these. Score out of 10. Questions: {st.session_state.test_q}. Answers: {u_ans}")
            st.success(res)
            # Logic for dashboard
            try: score = int(''.join(filter(str.isdigit, res.split('/10')[0][-2:])))
            except: score = 5
            save_db("teacher", res, "grading", score)

# FLASHCARDS
with menu[2]:
    st.subheader("🧠 Brain Cards")
    if st.button("Auto-Generate from History"):
        context = " ".join([m["content"] for m in st.session_state.messages[-5:]])
        cards = ask_ai(f"Create 3 flashcards from this text: {context}. Format: Front: [Q] | Back: [A]")
        st.write(cards)
        # In a real app, parse and save to flashcards table

# DASHBOARD
with menu[3]:
    st.subheader("📈 Performance")
    hist = supabase.table("history").select("*").eq("user_id", st.session_state.user_uuid).execute()
    if hist.data:
        df = pd.DataFrame(hist.data)
        if not df.empty and 'score' in df.columns:
            st.line_chart(df[df['score'] > 0]['score'])
            st.write("Scores tracking based on Teacher Mode results.")


# SCHEDULER
with menu[4]:
    s = st.text_input("Subjects")
    if st.button("Create Schedule"):
        st.markdown(ask_ai(f"Hourly schedule for {s}."))
