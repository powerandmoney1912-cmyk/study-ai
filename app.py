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
    .premium-badge { color: #FFD700; font-weight: bold; border: 1px solid #FFD700; padding: 2px 5px; border-radius: 5px; margin-left: 10px; }
    </style>
    <div class="footer">Built by Aarya Venkat | AI that turns notes into active recall sessions</div>
""", unsafe_allow_html=True)

# --- 2. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("🧠 Study Master Pro")
    st.markdown("---")
    menu = st.radio("Navigation", ["💬 Chat", "📝 Quiz Mode", "📅 Study Plan", "⚙️ Settings"])
    st.markdown("---")
    
    # Premium Access Logic
    access_code = st.text_input("Enter Premium Code:", type="password")
    is_premium = (access_code == "STUDY2026")
    model_name = 'gemini-1.5-flash' if is_premium else 'gemini-1.5-flash' # Using Flash for speed
    
    if is_premium:
        st.markdown('<span class="premium-badge">✨ PREMIUM ACTIVE</span>', unsafe_allow_html=True)
    
    if st.button("🗑️ Clear Conversation"):
        st.session_state.messages = []
        if "vector_store" in st.session_state:
            del st.session_state.vector_store
        st.rerun()

# --- 3. THE RAG ENGINE (Smart PDF Processing) ---
def process_pdf(file):
    try:
        # Read text from PDF
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:  # Check if text was extracted
                text += extracted
        
        if not text.strip():  # Check if any text was extracted
            st.error("No text could be extracted from the PDF. Please ensure it's not a scanned image.")
            return None
        
        # Split text into manageable chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(text)
        
        # Create Vector Store (Searchable index)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=st.secrets["GOOGLE_API_KEY"])
        vector_store = FAISS.from_texts(chunks, embedding=embeddings)
        return vector_store
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

# --- 4. PAGE LOGIC ---

# PAGE: CHAT
if menu == "💬 Chat":
    st.header("Chat with your Notes")
    
    uploaded_file = st.file_uploader("Upload your study PDF", type="pdf")
    
    if uploaded_file:
        if "vector_store" not in st.session_state:
            with st.spinner("Analyzing document with RAG..."):
                vector_store = process_pdf(uploaded_file)
                if vector_store is not None:
                    st.session_state.vector_store = vector_store
                    st.success("Analysis complete! I'm ready to answer specific questions.")
                else:
                    st.error("Failed to process the PDF. Please try another file.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Handle Input
    if prompt := st.chat_input("Ask me anything about your notes..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Retrieval Step: Find relevant chunks
        context = ""
        if "vector_store" in st.session_state:
            try:
                docs = st.session_state.vector_store.similarity_search(prompt, k=3)
                context = "\n".join([d.page_content for d in docs])
            except Exception as e:
                st.error(f"Error searching vector store: {str(e)}")
                context = ""

        # Generate Response using Gemini
        try:
            genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
            model = genai.GenerativeModel(model_name)
            
            full_prompt = f"""
            You are Study Master Pro, a professional tutor. 
            Context from PDF: {context}
            User Question: {prompt}
            
            Instructions: Use the context above to answer. If the answer isn't in the context, use your general knowledge but mention it's not in the notes.
            """
            
            response = model.generate_content(full_prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})

# PAGE: QUIZ MODE
elif menu == "📝 Quiz Mode":
    st.header("🎯 Active Recall Quiz")
    st.write("Select a mode to test your knowledge based on your notes.")
    quiz_type = st.selectbox("Mode", ["📘 Concept Check", "🧠 Application Mode", "🎯 Exam Mode"])
    
    if st.button("Generate Question"):
        if "vector_store" not in st.session_state:
            st.warning("Please upload a PDF in the Chat section first!")
        else:
            st.info("Generating a question based on your uploaded PDF context...")
            # Add Logic for specific quiz generation here
            # Example implementation:
            try:
                genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
                model = genai.GenerativeModel(model_name)
                
                # Get random chunks from vector store
                all_docs = st.session_state.vector_store.similarity_search("", k=5)
                context = "\n".join([d.page_content for d in all_docs[:3]])
                
                quiz_prompt = f"""
                Based on this content: {context}
                
                Generate a {quiz_type} question with 4 multiple choice options and indicate the correct answer.
                """
                
                response = model.generate_content(quiz_prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"Error generating quiz: {str(e)}")

# PAGE: STUDY PLAN
elif menu == "📅 Study Plan":
    st.header("Daily Micro-Task Generator")
    subj = st.text_input("What subject are you studying?")
    days = st.slider("Days until exam", 1, 30, 7)
    
    if st.button("Create Plan"):
        if subj:
            st.success(f"Plan generated for {subj}! (Feature coming soon in v3.1)")
        else:
            st.warning("Please enter a subject name first!")

# PAGE: SETTINGS
elif menu == "⚙️ Settings":
    st.header("App Settings")
    st.write("Customize your Study Master Pro experience.")
    theme = st.selectbox("Theme", ["Dark (Default)", "Light", "AMOLED"])
    st.info("Theme selection will be implemented in a future update.")
