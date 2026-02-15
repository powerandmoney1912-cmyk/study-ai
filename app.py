import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 0. GOOGLE VERIFICATION ---
st.markdown('<meta name="google-site-verification" content="ThWp6_7rt4Q973HycJ07l-jYZ0o55s8f0Em28jBBNoU" />', unsafe_allow_html=True)

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# API Setup
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("API Key missing in Secrets!")

def get_working_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for target in ['models/gemini-1.5-flash', 'models/gemini-pro']:
            if target in available_models: return target
        return available_models[0]
    except: return "gemini-pro"

MODEL_ID = get_working_model()

# --- 2. SIDEBAR ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    # I have simplified these names to prevent the NameError you saw
    menu = st.radio("Navigation", ["Chat", "Quiz Mode", "Study Plan"])
    st.divider()
    if st.button("🗑️ Reset App"):
        st.session_state.clear()
        st.rerun()

# --- 3. HELPER FUNCTIONS ---
def process_pdf(file):
    reader = PdfReader(file)
    text = "".join([page.extract_text() or "" for page in reader.pages])
    text_splitter = RecursiveCharacterTextSplitter(chunk_
