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
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_text(text)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=API_KEY)
    return FAISS.from_texts(chunks, embedding=embeddings)

def call_ai(prompt):
    model = genai.GenerativeModel(MODEL_ID)
    return model.generate_content(prompt).text

# --- 4. MAIN PAGES ---

# Fixed the menu comparison logic here
if menu == "Chat":
    st.header("💬 Chat with your Notes")
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    
    if uploaded_file and "vector_store" not in st.session_state:
        with st.spinner("Analyzing..."):
            st.session_state.vector_store = process_pdf(uploaded_file)
        st.success("Ready!")

    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        context = ""
        if "vector_store" in st.session_state:
            docs = st.session_state.vector_store.similarity_search(prompt, k=3)
            context = "\n".join([d.page_content for d in docs])
        response = call_ai(f"Context: {context}\n\nQuestion: {prompt}")
        with st.chat_message("assistant"): st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

elif menu == "Quiz Mode":
    st.header("📝 Quiz System")
    tab1, tab2 = st.tabs(["Subject Quiz", "Notes Quiz"])
    with tab1:
        subj = st.selectbox("Subject", ["English", "Maths", "Science"])
        if st.button("Generate"):
            st.markdown(call_ai(f"Create a quiz for {subj}"))
    with tab2:
        if "vector_store" not in st.session_state:
            st.warning("Upload a PDF first!")
        elif st.button("Generate from Notes"):
            docs = st.session_state.vector_store.similarity_search("concepts", k=4)
            st.markdown(call_ai(f"Quiz based on: {docs}"))

elif menu == "Study Plan":
    st.header("📅 Planner")
    topic = st.text_input("Topic?")
    if st.button("Create"):
        st.markdown(call_ai(f"Create a study plan for {topic}"))
