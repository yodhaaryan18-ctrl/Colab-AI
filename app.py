from geopy.geocoders import Nominatim
import streamlit as st
from google import genai
from PIL import Image
from groq import Groq
import requests
import PyPDF2
import pandas as pd
from bs4 import BeautifulSoup
import re
from supabase import create_client, Client

# 1. Connect to the AI Brains & Database
GEMINI_KEY = st.secrets["GEMINI_KEY"]
GROQ_KEY = st.secrets["GROQ_KEY"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

gemini_client = genai.Client(api_key=GEMINI_KEY)
groq_client = Groq(api_key=GROQ_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Initialize Memory from Cloud Database
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    try:
        # Fetch all past messages from Supabase, ordered by time
        response = supabase.table("messages").select("*").order("id").execute()
        for row in response.data:
            prefix = "User: " if row["role"] == "user" else "Colab Bot: "
            st.session_state.chat_history.append(f"{prefix}{row['content']}")
    except Exception as e:
        st.warning(f"Could not load cloud memory: {e}")

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
    section[data-testid="stSidebar"] { background-color: #1E1E1E !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)
st.markdown('<h1 class="premium-title">Tan Chat Bot</h1>', unsafe_allow_html=True)

# 4. Sidebar: The "Command Center"
voice_input_text = ""
with st.sidebar:
    st.header("🎙️ Voice Studio")
    audio_data = st.audio_input("Speak to the bot")
    if audio_data:
        with st.spinner("Transcribing..."):
            try:
                transcription = groq_client.audio.transcriptions.create(
                    file=("audio.wav", audio_data.read()),
                    model="whisper-large-v3",
                )
                voice_input_text = transcription.text
                st.success(f"Captured: {voice_input_text[:30]}...")
            except Exception as e:
                st.error(f"Voice Error: {e}")

    st.divider()
    st.header("⚙️ File Uploads")
    uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
    img = Image.open(uploaded_file) if uploaded_file else None
    
    uploaded_pdf = st.file_uploader("Upload PDF", type=['pdf'])
    pdf_text = ""
    if uploaded_pdf:
        try:
            pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
            for page in pdf_reader.pages: 
                pdf_text += page.extract_text() + "\n"
            st.success("PDF Loaded successfully!")
        except Exception:
            st.warning("Could not read text from this PDF.")
        
    uploaded_csv = st.file_uploader("Upload CSV", type=['csv'])
    csv_context = ""
    if uploaded_csv:
        try:
            df = pd.read_csv(uploaded_csv)
            csv_context = f"Data Summary:\n{df.head(10).to_markdown()}"
            st.success("CSV Loaded successfully!")
        except Exception:
            st.warning("Could not read this CSV.")

    if st.button("🗑️ Clear Cloud Memory"):
        # Danger zone: This deletes the database rows!
        supabase.table("messages").delete().neq("id", 0).execute() 
        st.session_state.chat_history = []
        st.rerun()

# 5. Welcome Message & History
if len(st.session_state.chat_history) == 0:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown("### Welcome to the Studio! ✨\nI am online and ready to help. Try asking me a complex question, giving me a website link to read, or telling me to draw something.")

for message in st.session_state.chat_history:
    role = "user" if message.startswith("User:") else "assistant"
    avatar = "👤" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.write(message.split(": ", 1)[1])

# 6. Main Chat Input 
user_input = st.chat_input("Ask anything...")

final_input = voice_input_text if voice_input_text else user_input

# 7. Processing Logic
if final_input:
    st.chat_message("user", avatar="👤").write(final_input)
    st.session_state.chat_history.append(f"User: {final_input}")
    
    with st.spinner("Agent routing request..."):
        # 🧠 UPDATED ROUTER: Now includes Maps!
        router_prompt = f"""Analyze the user's input and decide the best tool to use.
        Reply ONLY with one of these exactly matching words:
        IMAGE (If they want you to create or generate a picture)
        SCRAPE (If they provide a web link to summarize)
        MAP (If they ask to see a map, locate a city, or find a place)
        CHAT (For everything else)
        
        User Input: {final_input}"""
        
        try:
            intent = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": router_prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.1 
            ).choices[0].message.content.strip().upper()
        except:
            intent = "CHAT"
            
    st.caption(f"⚙️ *System: Request routed to {intent} Tool*")

    # 🛠️ TOOL 1: THE ARTIST 
    if "IMAGE" in intent:
        with st.chat_message("assistant", avatar="🎨"):
            with st.spinner("Painting your image..."):
                import urllib.parse
                clean_input = final_input.strip()
                encoded_prompt = urllib.parse.quote(clean_input)
                url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"
                try:
                    st.image(url, caption=f"Generated: {clean_input}")
                    supabase.table("messages").insert({"role": "user", "content": final_input}).execute()
                    supabase.table("messages").insert({"role": "assistant", "content": "[Generated Image]"}).execute()
                    st.session_state.chat_history.append("Colab Bot: [Generated Image]")
                except Exception:
                    st.error("Image server overloaded.")

    # 🛠️ TOOL 2: THE RESEARCHER 
    elif "SCRAPE" in intent:
        with st.chat_message("assistant", avatar="🔍"):
            url_match = re.search(r'(https?://\S+)', final_input)
            if url_match:
                with st.spinner("Reading website..."):
                    try:
                        res = requests.get(url_match.group(0), headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        soup = BeautifulSoup(res.text, 'html.parser')
                        url_context = " ".join([p.get_text() for p in soup.find_all('p')])[:3000]
                        summary = groq_client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "Summarize the provided website content clearly."}, 
                                {"role": "user", "content": f"User asked: {final_input}\n\nWebsite Content:\n{url_context}"}
                            ],
                            model="llama-3.3-70b-versatile",
                        ).choices[0].message.content
                        st.write(summary)
                        supabase.table("messages").insert({"role": "user", "content": final_input}).execute()
                        supabase.table("messages").insert({"role": "assistant", "content": summary}).execute()
                        st.session_state.chat_history.append(f"Colab Bot: {summary}")
                    except Exception as e:
                        st.error(f"Could not read website: {e}")
            else:
                st.warning("No valid link found.")

    # 🛠️ TOOL 3: THE NAVIGATOR (NEW!)
    elif "MAP" in intent:
        with st.chat_message("assistant", avatar="🗺️"):
            with st.spinner("Locating coordinates..."):
                try:
                    # 1. Ask the AI to extract JUST the location name from the prompt
                    location_name = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": f"Extract ONLY the city, country, or location name from this text: '{final_input}'. Return only the name."}],
                        model="llama-3.3-70b-versatile",
                        temperature=0.1
                    ).choices[0].message.content.strip()
                    
                    # 2. Get the GPS coordinates
                    geolocator = Nominatim(user_agent="colab_bot_agent")
                    location = geolocator.geocode(location_name)
                    
                    if location:
                        st.write(f"Dropping a pin at **{location.address}**")
                        # 3. Streamlit needs the GPS data in a DataFrame
                        map_data = pd.DataFrame({'lat': [location.latitude], 'lon': [location.longitude]})
                        st.map(map_data, zoom=12) # Streamlit's built-in interactive map!
                        
                        supabase.table("messages").insert({"role": "user", "content": final_input}).execute()
                        supabase.table("messages").insert({"role": "assistant", "content": f"[Map of {location_name}]"}).execute()
                        st.session_state.chat_history.append(f"Colab Bot: [Map of {location_name}]")
                    else:
                        st.warning("I couldn't find that specific location on the globe.")
                except Exception as e:
                    st.error(f"Navigation error: {e}")

    # 🛠️ TOOL 4: THE MASTER BRAIN 
    else:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                full_prompt = f"User Question: {final_input}\nContext from PDF: {pdf_text[:1500]}\nCSV Context: {csv_context}"
                target_model = 'gemini-2.5-flash' 
                try:
                    if img:
                        gem_res = gemini_client.models.generate_content(model=target_model, contents=[img, full_prompt]).text
                    else:
                        gem_res = gemini_client.models.generate_content(model=target_model, contents=full_prompt).text
                    
                    bot_persona = """You are Colab Chat Bot, a highly conversational, warm, and friendly AI assistant created by Yodha. 
                    When a user asks about your personal preferences, feelings, or true nature, respond exactly in this tone and style:
                    "I'm glad you're excited to chat with me. However, I should clarify that I don't have personal preferences... I'm a complex software program... But despite these limitations, I'm constantly learning and improving. How can I assist you today?"
                    For all other questions, maintain this same humble, human-like, and welcoming tone."""

                    final_res = groq_client.chat.completions.create(
                        messages=[{"role": "system", "content": bot_persona}, 
                                  {"role": "user", "content": gem_res}],
                        model="llama-3.3-70b-versatile",
                    ).choices[0].message.content
                    
                    st.write(final_res)
                    supabase.table("messages").insert({"role": "user", "content": final_input}).execute()
                    supabase.table("messages").insert({"role": "assistant", "content": final_res}).execute()
                    st.session_state.chat_history.append(f"Colab Bot: {final_res}")
                
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        st.warning("⏳ Google's free tier needs a 1-minute cooldown. Please wait 60 seconds.")
                    else:
                        st.error(f"Google API Error: {error_msg}")
