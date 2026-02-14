import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="AI Study Buddy", page_icon="📚")
st.title("🎓 My AI Study Assistant")

# This looks for your secret key once we upload it to the web
if "AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg" in st.secrets:
    genai.configure(api_key=st.secrets["AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg!")

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
        response = model.generate_content(prompt)
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})