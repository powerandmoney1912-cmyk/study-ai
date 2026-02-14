import streamlit as st
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="AI Study Master", page_icon="🎓")
st.title("🎓 AI Study Master")

# 2. API Key Setup
if "GOOGLE_API_KEY" not in st.secrets:
    st.error("Missing API Key in Streamlit Secrets!")
    st.stop()

# 3. Initialize the AI
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Use the correct model name
model = genai.GenerativeModel('gemini-1.5-flash-latest')

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
            # Generate response
            response = model.generate_content(prompt)
            
            # Check if response has text
            if response.text:
                st.markdown(response.text)
                # Save assistant response to history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response.text
                })
            else:
                st.warning("No response generated. Please try again.")
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Try rephrasing your question or check your API key permissions.")
