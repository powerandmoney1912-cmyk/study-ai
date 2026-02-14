import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Study Master Pro", page_icon="🎓")
st.title("🎓 Study Master Pro")

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Add GOOGLE_API_KEY to Secrets!")
    st.stop()

# Stable Initialization
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What are we learning today?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Technical Error: {e}")
