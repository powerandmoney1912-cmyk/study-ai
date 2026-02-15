import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")

# Get API Key from Secrets
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)

# --- 2. THE ULTIMATE MODEL FIX ---
def get_working_model():
    """Finds the best available model for your specific API key"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer Flash for speed, fallback to Pro, then pick whatever is first
        for target in ['models/gemini-1.5-flash', 'models/gemini-pro', 'models/gemini-1.5-flash-8b']:
            if target in available_models:
                return target
        return available_models[0] if available_models else "gemini-pro"
    except:
        return "gemini-pro"

MODEL_ID = get_working_model()

# --- 3. UI BRANDING ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0e1117; color: white; }}
    .footer {{ position: fixed; left: 0; bottom: 0; width: 100%; text-align: center; color: #6e7681; font-size: 14px; padding: 10px; background: #0e1117; z-index: 100; }}
    </style>
    <div class="footer">Built by Aarya Venkat | Running on {MODEL_ID}</div>
""", unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan"])
    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- 5. RAG ENGINE ---
def process_pdf(file):
    reader = PdfReader(file)
    text = "".join([page.extract_text() or "" for page in reader.pages])
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    
    # Use standard embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=API_KEY)
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    return vector_store

# --- 6. MAIN CHAT ---
if menu == "💬 Chat":
    st.header("Chat with your Notes")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    
    if uploaded_file and "vector_store" not in st.session_state:
        with st.spinner("Analyzing..."):
            st.session_state.vector_store = process_pdf(uploaded_file)
        st.success("Analysis complete!")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask about your notes..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        context = ""
        if "vector_store" in st.session_state:
            docs = st.session_state.vector_store.similarity_search(prompt, k=3)
            context = "\n".join([d.page_content for d in docs])

        try:
            model = genai.GenerativeModel(MODEL_ID)
            response = model.generate_content(f"Context: {context}\n\nUser Question: {prompt}")
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Error: {e}")
