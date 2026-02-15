import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

# --- 1. SETTINGS & BRANDING ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

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
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan", "⚙️ Settings"])
    
    st.markdown("---")
    # Using 'on_change' to ensure it processes the code immediately
    access_input = st.text_input("Premium Code:", type="password", key="premium_code")
    
    is_premium = (access_input == "STUDY2026")
    
    # ULTIMATE 404 FIX: Using the most stable model names possible
    if is_premium:
        current_model = 'gemini-1.5-pro' 
        st.markdown('<div class="premium-badge">✨ PREMIUM ACTIVE</div>', unsafe_allow_html=True)
    else:
        current_model = 'gemini-1.5-flash'
        st.info("Using Free Tier")
    
    st.markdown("---")
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 3. RAG ENGINE ---
def process_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content
            
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    
    # Ensure this model name is also correct
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=st.secrets["GOOGLE_API_KEY"])
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    return vector_store

# --- 4. CHAT PAGE ---
if menu == "💬 Chat":
    st.header("Chat with your Notes")
    
    uploaded_file = st.file_uploader("Upload Study PDF", type="pdf")
    if uploaded_file and "vector_store" not in st.session_state:
        with st.spinner("Analyzing..."):
            st.session_state.vector_store = process_pdf(uploaded_file)
        st.success("Done! Ask me anything.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Type your question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        context = ""
        if "vector_store" in st.session_state:
            docs = st.session_state.vector_store.similarity_search(prompt, k=3)
            context = "\n".join([d.page_content for d in docs])

        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            # Remove 'models/' prefix if it fails - some versions need it, some don't.
            # We will try the most common one first.
            model = genai.GenerativeModel(current_model)
            
            full_prompt = f"Context: {context}\n\nUser Question: {prompt}"
            response = model.generate_content(full_prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"AI Connection Error. Details: {e}")

else:
    st.info(f"Page '{menu}' is locked or under construction. Go to Chat to upload notes!")
