import streamlit as st
from google import genai
from PIL import Image
from groq import Groq
import requests
import PyPDF2
import pandas as pd
from bs4 import BeautifulSoup
import re

# 1. Connect to the AI Brains (STEP 2: SECURED VIA SECRETS)
GEMINI_KEY = st.secrets["GEMINI_KEY"]
GROQ_KEY = st.secrets["GROQ_KEY"]

gemini_client = genai.Client(api_key=GEMINI_KEY)
groq_client = Groq(api_key=GROQ_KEY)

# 2. Initialize Memory
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 3. Page Setup & Premium Dark Theme CSS
st.set_page_config(page_title="Colab Chat Bot", page_icon="✨", layout="centered")

custom_css = """
<style>
    .stApp { background-color: #121212; color: #E0E0E0; }
    .premium-title {
        font-size: 3rem; font-weight: 800; text-align: center;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 20px;
    }
    .stChatInputContainer { border-radius: 25px !important; }
    /* Style the sidebar a bit */
    section[data-testid="stSidebar"] { background-color: #1E1E1E !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<h1 class="premium-title">Colab Chat Bot</h1>', unsafe_allow_html=True)

# 4. Sidebar: The "Command Center"
voice_input_text = ""
with st.sidebar:
    st.header("🎙️ Voice Studio")
    audio_data = st.audio_input("Speak to the bot")
    if audio_data:
        with st.spinner("Transcribing..."):
            transcription = groq_client.audio.transcriptions.create(
                file=("audio.wav", audio_data.read()),
                model="whisper-large-v3",
            )
            voice_input_text = transcription.text
            st.success(f"Captured: {voice_input_text[:30]}...")

    st.divider()
    st.header("⚙️ File Uploads")
    uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
    img = Image.open(uploaded_file) if uploaded_file else None
    
    uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'])
    pdf_text = ""
    if uploaded_pdf:
        pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
        for page in pdf_reader.pages: pdf_text += page.extract_text() + "\n"
        
    uploaded_csv = st.file_uploader("Upload CSV", type=['csv'])
    csv_context = ""
    if uploaded_csv:
        df = pd.read_csv(uploaded_csv)
        csv_context = f"Data Summary:\n{df.head(10).to_markdown()}"

    if st.button("🗑️ Clear Memory"):
        st.session_state.chat_history = []
        st.rerun()

# 5. Display History
for message in st.session_state.chat_history:
    role = "user" if message.startswith("User:") else "assistant"
    avatar = "👤" if role == "user" else "✨"
    with st.chat_message(role, avatar=avatar):
        st.write(message.split(": ", 1)[1])

# 6. Main Chat Input (Standard & Sleek)
user_input = st.chat_input("Ask anything...")

# If voice was used, it overrides the text input
final_input = voice_input_text if voice_input_text else user_input

# 7. Processing Logic
if final_input:
    st.chat_message("user", avatar="👤").write(final_input)
    st.session_state.chat_history.append(f"User: {final_input}")
    
    # --- Check for Links to Scrape ---
    url_context = ""
    url_match = re.search(r'(https?://\S+)', final_input)
    if url_match:
        try:
            res = requests.get(url_match.group(0), headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(res.text, 'html.parser')
            url_context = " ".join([p.get_text() for p in soup.find_all('p')])[:2000]
        except: pass

    # --- IMAGE GENERATION CHECK ---
    if any(word in final_input.lower() for word in ["draw", "image", "picture", "paint"]):
        with st.chat_message("assistant", avatar="🎨"):
            url = f"https://image.pollinations.ai/prompt/{final_input.replace(' ', '%20')}?nologo=true"
            st.markdown(f'<img src="{url}" width="100%" style="border-radius: 15px;">', unsafe_allow_html=True)
            st.session_state.chat_history.append(f"Colab Bot: [Generated Image]")
    
   # --- MASTER BRAIN RESPONSE ---
else:
    with st.chat_message("assistant", avatar="✨"):
        with st.spinner("Thinking..."):
            full_prompt = f"User Question: {final_input}\nContext from PDF: {pdf_text[:1500]}\nCSV Context: {csv_context}\nWeb Context: {url_context}"
            
            # Using the most stable model name for the GENAI library
            target_model = 'gemini-1.5-flash' 
            
            try:
                if img:
                    gem_res = gemini_client.models.generate_content(model=target_model, contents=[img, full_prompt]).text
                else:
                    gem_res = gemini_client.models.generate_content(model=target_model, contents=full_prompt).text
                
                # Final polish via Groq
                final_res = groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": "Combine context into a clear response."}, 
                              {"role": "user", "content": gem_res}],
                    model="llama-3.3-70b-versatile",
                ).choices[0].message.content
                
                st.write(final_res)
                st.session_state.chat_history.append(f"Colab Bot: {final_res}")
            except Exception as e:
                st.error(f"Model Error: {e}")
                st.info("Tip: Try changing the model name to 'models/gemini-1.5-flash' in the code.")
                ).choices[0].message.content
                
                st.write(final_res)
                st.session_state.chat_history.append(f"Colab Bot: {final_res}")
