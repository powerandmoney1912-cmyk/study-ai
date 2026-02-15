import streamlit as st
import google.generativeai as genai

# Force the API to use a specific version to avoid the 404 v1beta bug
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

@st.cache_resource
def load_ai_model():
    # Attempt 1: Standard Name
    # Attempt 2: Legacy Name
    # Attempt 3: Pro Name
    for model_name in ['gemini-1.5-flash', 'models/gemini-1.5-flash', 'gemini-pro']:
        try:
            m = genai.GenerativeModel(model_name)
            # Verify the model actually responds
            m.generate_content("ping")
            return m
        except Exception:
            continue
    return None

model = load_ai_model()
