import streamlit as st
import google.generativeai as genai

# 1. PROFESSIONAL PAGE SETUP
st.set_page_config(page_title="Study Master Pro", page_icon="🎓", layout="wide")

# 2. SIDEBAR WITH EXTRA FEATURES
with st.sidebar:
    st.title("⚙️ AI Settings")
    st.markdown("---")
    
    # Feature: Creativity Control
    temp = st.slider("Creativity Level", 0.0, 1.0, 0.7)
    
    # Feature: Quick Actions
    st.subheader("Quick Actions")
    if st.button("🗑️ Clear All Chat"):
        st.session_state.messages = []
        st.rerun()
        
    # Feature: Export Chat
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        chat_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
        st.download_button("📥 Download Study Notes", chat_text, file_name="study_notes.txt")

# 3. API INITIALIZATION (THE BUG FIX)
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ KEY MISSING: Add GOOGLE_API_KEY to Streamlit Secrets.")
    st.stop()

# Force v1 connection by using the latest stable library methods
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(
    model_name='gemini-1.5-flash',
    generation_config={"temperature": temp}
)

# 4. CHAT INTERFACE
st.title("🎓 Study Master Pro")
st.info("I am your advanced tutor. Ask me to explain concepts, solve math, or quiz you!")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. INPUT & AI RESPONSE
if prompt := st.chat_input("What are we learning today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # The simple call prevents v1beta routing errors
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            # Detailed error reporting
            if "404" in str(e):
                st.error("Error 404: The model name is incorrect or the API version is outdated.")
            else:
                st.error(f"AI Connection Error: {e}")
