import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    start_time = time.time()
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()
        duration = round(time.time() - start_time, 2)
        return data['choices'][0]['message']['content'], duration
    except:
        return "⚠️ Error connecting to AI.", 0

def scrape_url_with_strict_filter(url):
    """
    Targets the Chicago Oracle portal. 
    Added 'radio' to keywords to capture telecommunications.
    """
    it_keywords = [
        "computer", "software", "network", "telecommunication", 
        "server", "technology", "hardware", "radio", "cabling"
    ]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Oracle tables often use 'span' or 'a' tags for bid titles
        elements = soup.find_all(['span', 'a', 'td'])
        filtered_results = []
        
        for el in elements:
            text = el.get_text(strip=True)
            if any(key in text.lower() for key in it_keywords):
                if text not in filtered_results:
                    filtered_results.append(text)
        
        return " | ".join(filtered_results)[:7000] if filtered_results else "No IT content found."
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Simplifier")

with st.sidebar:
    st.header("Project Performance")
    if 'total_saved' not in st.session_state: 
        st.session_state.total_saved = 0
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

# DATA SOURCE SELECTION
input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:", placeholder="https://eprocurement.cityofchicago.org/...")
    if url_input:
        with st.spinner("Scraping & Filtering..."):
            final_text = scrape_url_with_strict_filter(url_input)
            if "No IT content" in final_text:
                st.warning(final_text)
            else:
                st.success("Scrape complete. IT context found.")
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        final_text = "".join([p.extract_text() for p in reader.pages[:3]])

# ANALYSIS BUTTONS
if final_text and "Error" not in final_text:
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Simplify for Citizens"):
            role = "You are a plain-language expert."
            prompt = f"Summarize the IT/Radio goal of this bid in 2 sentences: {final_text}"
            ans, dur = query_groq(prompt, role)
            st.info(ans)
            st.session_state.total_saved += 5

    with col2:
        if st.button("Extract Technical Specs"):
            role = "You are a hardware auditor."
            # Instructing the AI that RADIOS count as IT Hardware
            prompt = (
                f"Identify IT gear, computers, or telecommunications equipment like Radios. "
                f"Ignore chemicals, dogs, and construction. "
                f"Text: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            st.success(ans)
            st.session_state.total_saved += 15

    with col3:
        if st.button("Reporting Guidance"):
            role = "Compliance officer."
            prompt = f"Identify reporting deadlines for this project: {final_text}"
            ans, dur = query_groq(prompt, role)
            st.warning(ans)
            st.session_state.total_saved += 10
