import streamlit as st
import google.generativeai as genai

# 1. Page Setup
st.set_page_config(page_title="AI Study Buddy", page_icon="📚")
st.title("🎓 My AI Study Assistant")

# 2. Setup API Key from Secrets (FIXED LINE)
if "AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg" in st.secrets:
    # This line now correctly looks for the label "AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg"
    genai.configure(api_key=st.secrets["AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg"])
    model = genai.GenerativeModel('gemini-1.5-flash')

# 3. Chat History Setup
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Display Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Chat Input
if prompt := st.chat_input("Ask me anything about your studies!"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = model.generate_content(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI Error: {e}")

