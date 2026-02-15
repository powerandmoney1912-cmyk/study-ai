import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

# --- 1. SETTINGS & BRANDING ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Custom Professional Styling
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: #6e7681; font-size: 14px; padding: 10px; background: #0e1117; z-index: 100; }
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 5px; border-radius: 5px; display: inline-block; margin-top: 10px; }
    </style>
    <div class="footer">Built by Aarya Venkat | AI that turns notes into active recall sessions</div>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    st.markdown("---")
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan", "⚙️ Settings"])
    st.markdown("---")
    
    # FIX: Premium Access Logic with Auto-Submit
    access_input = st.text_input("Enter Premium Code & Press Enter:", type="password", key="premium_key")
    
    # Check the code
    is_premium = (access_input == "STUDY2026")
    
    # FIX: Use a model name that is confirmed to exist in the 2026 API
    model_choice = 'gemini-1.5-flash' # Usually works, but if 404 persists, we use 'gemini-pro'
    
    if is_premium:
        st.markdown('<div class="premium-badge">✨ PREMIUM ACTIVE</div>', unsafe_allow_html=True)
    else:
        st.info("Using Free Tier (Flash-Lite)")
    
    st.markdown("---")
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        if "vector_store" in st.session_state:
            del st.session_state.vector_store
        st.rerun()

# --- 3. THE RAG ENGINE ---
def process_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=st.secrets["GOOGLE_API_KEY"])
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    return vector_store

# --- 4. PAGE LOGIC ---

if menu == "💬 Chat":
    st.header("Chat with your Notes")
    
    uploaded_file = st.file_uploader("Upload your study PDF", type="pdf")
    
    if uploaded_file:
        if "vector_store" not in st.session_state:
            with st.spinner("Analyzing document..."):
                st.session_state.vector_store = process_pdf(uploaded_file)
            st.success("PDF Ready!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Ask me anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        context = ""
        if "vector_store" in st.session_state:
            docs = st.session_state.vector_store.similarity_search(prompt, k=3)
            context = "\n".join([d.page_content for d in docs])

        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # Using the most stable model name to avoid 404
            model = genai.GenerativeModel('gemini-1.5-flash') 
            
            full_prompt = f"Context: {context}\n\nQuestion: {prompt}"
            response = model.generate_content(full_prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI Error: {e}. Try checking your API key or model name.")

elif menu == "📝 Quiz Mode":
    st.header("🎯 Active Recall Quiz")
    st.info("Upload a PDF in the Chat section first to generate custom questions!")

elif menu == "📅 Study Plan":
    st.header("Daily Micro-Task Generator")
    st.write("Feature coming in v3.1")

elif menu == "⚙️ Settings":
    st.header("App Settings")
    st.write("Dark Mode is active by default.")
