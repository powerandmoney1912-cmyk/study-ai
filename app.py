import streamlit as st
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="AI Study Master", page_icon="🎓")
st.title("🎓 AI Study Master")

# 2. API Key Setup
# We check if the key exists in your Secrets box
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

# 3. Initialize the AI (The "Bug-Killer" way)
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# We use the most direct model name to avoid the 404 error
model = genai.GenerativeModel('gemini-1.5-flash')

# 4. Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Show previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. User Input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        try:
            # Direct generation call
            response = model.generate_content(prompt)
            st.markdown(response.text)
            # Save assistant response to history
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            # If it fails, this will tell us exactly why
            st.error(f"Error: {e}")
