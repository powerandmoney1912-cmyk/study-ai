import streamlit as st
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="Study Master Pro", page_icon="🎓")
st.title("🎓 Study Master Pro")

# 2. API Key Check
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing GOOGLE_API_KEY in Streamlit Secrets!")
    st.stop()

# 3. Setup AI (Direct Connection)
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
# Using the most stable model name
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Interaction
if prompt := st.chat_input("What are we learning today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # This is where the magic happens
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Technical Error: {e}")
            st.info("If you see 'v1beta' in the error above, make sure you created requirements.txt!")
