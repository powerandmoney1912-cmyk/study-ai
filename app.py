import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os

# --- 1. SETTINGS & BRANDING ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Professional CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: white; }
    .footer { position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: #6e7681; font-size: 14px; padding: 10px; background: #0e1117; z-index: 100; }
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 2px 5px; border-radius: 5px; }
    </style>
    <div class="footer">Built by Aarya Venkat | AI that turns notes into active recall sessions</div>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan", "⚙️ Settings"])
    st.divider()
    
    # Premium Logic
    access_code = st.text_input("Premium Code:", type="password")
    is_premium = (access_code == "STUDY2026")
    model_name = 'gemini-2.5-flash' if is_premium else 'gemini-2.5-flash-lite'
    
    if is_premium: st.success("✨ Premium Active")

# --- 3. THE "REAL RAG" ENGINE (Smarter PDF Reading) ---
def process_pdf(file):
    reader = PdfReader(file)
    text = "".join([page.extract_text() for page in reader.pages])
    
    # Split PDF into chunks (Upgrade A)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    
    # Create Embeddings & Store in FAISS
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=st.secrets["GOOGLE_API_KEY"])
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    return vector_store

# --- 4. PAGE LOGIC ---

# PAGE: CHAT
if menu == "💬 Chat":
    st.header("Chat with your Notes")
    uploaded_file = st.file_uploader("Upload PDF for Context", type="pdf")
    
    if uploaded_file:
        if "vector_store" not in st.session_state:
            with st.spinner("Analyzing document..."):
                st.session_state.vector_store = process_pdf(uploaded_file)
            st.success("Document Indexed!")

    # Chat UI
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask about your notes..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        # Retrieval Step
        context = ""
        if "vector_store" in st.session_state:
            docs = st.session_state.vector_store.similarity_search(prompt, k=3)
            context = "\n".join([d.page_content for d in docs])

        # Generate Response
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        model = genai.GenerativeModel(model_name)
        full_prompt = f"Context: {context}\n\nUser Question: {prompt}"
        
        response = model.generate_content(full_prompt)
        with st.chat_message("assistant"):
            st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

# PAGE: QUIZ MODE (Upgrade B)
elif menu == "📝 Quiz Mode":
    st.header("🎯 Active Recall Quiz")
    mode = st.selectbox("Select Mode", ["📘 Concept Check", "🧠 Application", "🎯 Exam Mode (Timed)"])
    if st.button("Start Quiz"):
        st.write(f"Generating {mode} questions...")
        # (Logic for quiz generation goes here)

# PAGE: STUDY PLAN (Upgrade C)
elif menu == "📅 Study Plan":
    st.header("Daily Micro-Tasks")
    subject = st.text_input("Subject")
    exam_date = st.date_input("Exam Date")
    if st.button("Generate Schedule"):
        st.info("Creating your personalized path to success...")
