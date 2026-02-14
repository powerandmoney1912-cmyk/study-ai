import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Study Master Pro", page_icon="🎓")
st.title("🎓 Study Master Pro")

# Use the stable version reference
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # gemini-2.5-flash is the stable auto-updated alias for 2026
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    st.error("API Key missing in Secrets!")
    st.stop()

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
            st.error(f"Error: {e}")
