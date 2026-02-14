import streamlit as st
import google.generativeai as genai

# 1. Setup the Page
st.set_page_config(page_title="AI Study Master Pro", page_icon="🎓", layout="wide")
st.title("🎓 AI Study Master Pro")
st.caption("Your personalized academic assistant, powered by Google Gemini")

# 2. Setup the Sidebar
with st.sidebar:
    st.title("⚙️ Settings")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# 3. Securely Load the API Key
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ Secret Key Missing! Add 'GOOGLE_API_KEY' to Streamlit Secrets.")
    st.stop()

# 4. Initialize the AI Model (THE BUG FIX)
# We use 'gemini-1.5-flash' which is the most stable version
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

# 5. Handle Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Chat Interaction
if prompt := st.chat_input("What are we studying today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Simple, clean generation call
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI Connection Error: {e}")
