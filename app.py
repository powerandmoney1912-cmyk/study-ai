import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# --- 0. GOOGLE VERIFICATION ---
# This hidden tag tells Google you own the site.
st.markdown('<meta name="google-site-verification" content="PASTE_YOUR_CODE_HERE" />', unsafe_allow_html=True)

# --- 1. SETUP ---
st.set_page_config(page_title="Study Master Pro", layout="wide")
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)

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
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan"])
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

if menu == "💬 Chat":
    st.header("💬 Chat with your Notes")
    uploaded_file = st.file_uploader("Upload PDF to unlock 'Custom Quiz'", type="pdf")
    if uploaded_file and "vector_store" not in st.session_state:
        with st.spinner("Analyzing..."):
            st.session_state.vector_store = process_pdf(uploaded_file)
        st.success("PDF analyzed! You can now use 'Based on my notes' in Quiz Mode.")

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

# --- QUIZ MODE (NEW LOGIC) ---
elif menu == "📝 Quiz Mode":
    st.header("📝 Advanced Quiz System")
    
    tab1, tab2 = st.tabs(["📚 Subject Quiz", "📖 Based on My Notes"])
    
    with tab1:
        diff = st.select_slider("Select Difficulty", options=["Easy", "Hard", "Impossible"])
        subj = st.selectbox("Select Subject", ["English", "Maths", "Social Science", "Science", "Tamil", "Hindi", "Malayalam", "Telugu", "Kannada", "Marathi"])
        count = st.number_input("Number of Questions", min_value=1, max_value=20, value=5)
        
        if st.button("Generate Subject Quiz"):
            with st.spinner(f"Creating {diff} {subj} Quiz..."):
                prompt = f"Create a {diff} difficulty quiz for the subject {subj}. Generate {count} questions. Provide questions first, then a clear answer key at the end."
                st.markdown(call_ai(prompt))

    with tab2:
        if "vector_store" not in st.session_state:
            st.warning("⚠️ Please upload a PDF in the Chat section first!")
        else:
            q_count = st.number_input("Questions from your notes", min_value=1, max_value=20, value=5)
            if st.button("Generate Custom Quiz"):
                with st.spinner("Scanning your study notes..."):
                    docs = st.session_state.vector_store.similarity_search("key definitions and concepts", k=4)
                    context = "\n".join([d.page_content for d in docs])
                    prompt = f"Based on this context: {context}\n\nGenerate {q_count} questions to test the user's knowledge. Provide an answer key."
                    st.markdown(call_ai(prompt))

# --- STUDY PLAN ---
elif menu == "📅 Study Plan":
    st.header("📅 Daily Study Planner")
    st.info("💡 Pro Tip: Finish your Quiz first, then come here to organize your next session!")
    days = st.slider("Days until exam?", 1, 30, 7)
    topic = st.text_input("What is the main topic?")
    if st.button("Create Plan"):
        plan = call_ai(f"Create a {days}-day study plan for {topic}. Be specific.")
        st.markdown(plan)
