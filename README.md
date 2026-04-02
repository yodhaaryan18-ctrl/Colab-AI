# 🤖 Colab Chat Bot: Autonomous AI Agent

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](YOUR_STREAMLIT_URL_HERE)

An advanced, multi-modal AI Agent built with Python and Streamlit. This bot goes beyond basic chat by using a custom **Agentic Router** to dynamically analyze user intent and select the appropriate tool for the job.

### ✨ Live Demo
Try the live application here: **[Link to your Streamlit App]**

---

## 🚀 Key Features

* **🧠 Agentic Routing:** Uses an ultra-fast Groq Llama-3.3 model to classify user intent and route requests to specialized tools (Chat, Map, Scrape, or Image).
* **🗄️ Persistent Cloud Memory:** Integrates with **Supabase (PostgreSQL)** to permanently store chat history, allowing the bot to remember past interactions across sessions.
* **🗺️ Interactive GPS Mapping:** Extracts location data and generates interactive, zoomable UI maps using `Geopy`.
* **🎨 Image Generation:** Creates custom images on demand using the Pollinations.ai API.
* **🔍 Web Scraping & Summarization:** Reads live websites (via `BeautifulSoup`) and provides intelligent summaries of the content.
* **📄 Document Analysis:** Native support for reading and analyzing uploaded PDFs and CSV files.

---

## 🛠️ Tech Stack

* **Frontend/UI:** Streamlit
* **LLM Routing Engine:** Groq (Llama-3.3-70b-versatile)
* **Master Reasoning Engine:** Google Gemini (2.5 Flash)
* **Database/Memory:** Supabase
* **Geocoding:** Geopy
* **Web Scraping:** BeautifulSoup4 & Requests

---

## 💻 Local Setup (For Developers)

If you want to run this project on your local machine:

1. Clone the repository:
   ```bash
   git clone [https://github.com/Yodhaaryan18-ctrl/Colab-AI.git](https://github.com/Yodhaaryan18-ctrl/Colab-AI.git)
