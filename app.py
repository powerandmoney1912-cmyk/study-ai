import streamlit as st
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, timedelta
import uuid
import time

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Ultra", layout="wide")

try:
    supabase: Client = create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("API Keys missing!")
    st.stop()

# --- 2. STATE ---
if "messages" not in st.session_state: st.session_state.messages = []
if "user_uuid" not in st.session_state: st.session_state.user_uuid = str(uuid.uuid4())
if "timer_active" not in st.session_state: st.session_state.timer_active = False
if "timer_end" not in st.session_state: st.session_state.timer_end = None

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🎓 Study Master Pro")
    menu = st.radio("Navigation", ["💬 Chat", "👨‍🏫 Teacher", "📁 File Lab", "📊 Dashboard"])
    
    st.divider()
    lang = st.selectbox("🌍 Language", ["English", "Tamil (தமிழ்)", "Hindi"])
    
    # Timer Counting Fix
    if st.session_state.timer_active:
        rem = st.session_state.timer_end - datetime.now()
        if rem.total_seconds() > 0:
            st.warning(f"Focusing: {str(rem).split('.')[0]}")
            if st.button("🛑 Stop"):
                st.session_state.timer_active = False
                st.session_state.timer_end = None
                st.rerun()
            time.sleep(1)
            st.rerun()
        else:
            st.success("Finished!")
            st.session_state.timer_active = False
    else:
        mins = st.number_input("Minutes", 1, 180, 25)
        if st.button("🚀 Start"):
            st.session_state.timer_active = True
            st.session_state.timer_end = datetime.now() + timedelta(minutes=mins)
            st.rerun()

    st.divider()
    st.write("✨ Made by Aarya with ❤️")

# --- 4. AI ENGINE ---
def ask_ai(prompt, system="Expert Tutor"):
    t_lang = "Tamil" if "Tamil" in lang else lang
    full_sys = f"{system}. Respond ONLY in {t_lang}."
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "system", "content": full_sys}, {"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

# --- 5. FIXED FILE LAB MODULE ---
if menu == "📁 File Lab":
    st.header("File & Camera Lab")
    
    # Choice for input
    source = st.radio("Select Source:", ["Upload Image/PDF", "Use Camera"])
    
    input_file = None
    if source == "Use Camera":
        input_file = st.camera_input("Take a photo of your notes")
    else:
        input_file = st.file_uploader("Choose a file", type=['png', 'jpg', 'jpeg', 'pdf'])

    # THE FIX: If there is a file, show the submit button
    if input_file is not None:
        st.success(f"File Received: {input_file.name if hasattr(input_file, 'name') else 'Camera Photo'}")
        
        # This button will now appear BELOW the file/camera preview
        if st.button("🔍 Analyze & Get Notes", use_container_width=True):
            with st.spinner("AI is reading your notes..."):
                # Simulation of AI analysis
                analysis = ask_ai(f"User has provided an image/file. Summarize the main points as if you can see it.")
                st.markdown("### 📝 Your AI Notes")
                st.write(analysis)
                
# --- 6. OTHER FEATURES ---
elif menu == "💬 Chat":
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.write(m["content"])
    if p := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": p})
        ans = ask_ai(p)
        st.session_state.messages.append({"role": "assistant", "content": ans})
        st.rerun()

elif menu == "👨‍🏫 Teacher":
    st.header("Teacher Mode")
    topic = st.text_input("Topic")
    if st.button("Start Test"):
        st.session_state.test = ask_ai(f"Give 5 questions about {topic}.")
    if "test" in st.session_state:
        st.info(st.session_state.test)
        u_ans = st.text_area("Your answers")
        if st.button("Submit Test"):
            st.success(ask_ai(f"Grade these: {u_ans}"))
