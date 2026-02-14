import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="AI Study Buddy", page_icon="📚")
st.title("🎓 My AI Study Assistant")

# Check if the secret exists
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg"])
    # We define 'model' here
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("API Key not found! Please add AIzaSyBT-8Xa8JZyIQKAF_XrymlkkRjLlBUmAJg to your Streamlit Secrets.")
    st.stop() # This stops the app so 'model' isn't called later

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
        # Now 'model' is guaranteed to exist because of st.stop() above
        response = model.generate_content(prompt)
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
