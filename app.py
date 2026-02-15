import streamlit as st
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, auth

# --- 1. FIREBASE SETUP ---
if not firebase_admin._apps:
    # This reads the [firebase] section from your Streamlit Secrets
    fb_secrets = st.secrets["firebase"]
    
    # We create a dictionary to pass to Firebase
    cred_dict = {
        "type": fb_secrets["type"],
        "project_id": fb_secrets["project_id"],
        "private_key_id": fb_secrets["private_key_id"],
        "private_key": fb_secrets["private_key"],
        "client_email": fb_secrets["client_email"],
        "client_id": fb_secrets["client_id"],
        "auth_uri": fb_secrets["auth_uri"],
        "token_uri": fb_secrets["token_uri"],
        "auth_provider_x509_cert_url": fb_secrets["auth_provider_x509_cert_url"],
        "client_x509_cert_url": fb_secrets["client_x509_cert_url"],
        "universe_domain": fb_secrets.get("universe_domain", "googleapis.com")
    }
    
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

# --- 2. GEMINI AI SETUP ---
# This fixes the "NotFound" error by using the updated model name
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash') #

# --- 3. THE APP INTERFACE ---
st.title("Study Master Pro 🎓")

if 'user' not in st.session_state:
    st.subheader("Login to start studying")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        try:
            # Note: For full production, you'd use a frontend login flow, 
            # but this verifies the user exists in your Firebase project.
            user = auth.get_user_by_email(email)
            st.session_state['user'] = user.email
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {e}")
else:
    st.write(f"Welcome, {st.session_state['user']}!")
    
    prompt = st.text_input("Ask your study question:")
    if prompt:
        with st.spinner("Thinking..."):
            # Generates text using the Flash model
            response = model.generate_content(prompt)
            st.markdown(response.text)

    if st.button("Log out"):
        del st.session_state['user']
        st.rerun()
