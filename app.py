import streamlit as st
import google.generativeai as genai
import time

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="AI Study Master Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLING & UI ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stChatMessage { border-radius: 15px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. API INITIALIZATION ---
# We define 'model' as None first so the app knows it exists
model = None

if "GOOGLE_API_KEY" not in st.secrets:
    st.error("❌ CRITICAL ERROR: GOOGLE_API_KEY not found in Streamlit Secrets.")
    st.stop()
else:
    try:
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_output_tokens": 2048,
        }
        # This creates the AI brain correctly
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash", 
            generation_config=generation_config
        )
    except Exception as e:
        st.error(f"Failed to connect to Google AI: {str(e)}")
        st.stop()

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    st.markdown("---")
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
    
    st.markdown("---")
    st.subheader("How to use:")
    st.write("1. Ask for study summaries.")
    st.write("2. Upload topics for practice quizzes.")
    st.write("3. Solve complex math or science.")
    
    st.info("Running on Gemini 1.5 Flash")

# --- 5. CHAT ENGINE ---
st.title("🎓 AI Study Master Pro")
st.caption("Your personalized academic assistant, powered by Google Gemini")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history from session state
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("What are we studying today?"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # Add a system instruction hidden from the user to improve quality
            contextual_prompt = f"System: You are a helpful, expert tutor. User says: {prompt}"
            response = model.generate_content(contextual_prompt)
            
            # Simulate streaming for a "pro" feel
            for chunk in response.text.split():
                full_response += chunk + " "
                time.sleep(0.02)
                message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")



