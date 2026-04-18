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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        data = response.json()
        duration = round(time.time() - start_time, 2)
        
        if "choices" in data:
            return data['choices'][0]['message']['content'], duration
        else:
            # This captures specific API errors like "Rate Limit"
            error_msg = data.get('error', {}).get('message', 'Unknown AI Error')
            return f"⚠️ Groq API says: {error_msg}", 0
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}", 0

def scrape_url_with_strict_filter(url):
    it_keywords = ["computer", "software", "network", "telecommunication", "server", "technology", "hardware", "radio", "cabling"]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        elements = soup.find_all(['span', 'a', 'td', 'p'])
        filtered_results = []
        for el in elements:
            text = el.get_text(strip=True)
            if any(key in text.lower() for key in it_keywords):
                if text not in filtered_results:
                    filtered_results.append(text)
        return " | ".join(filtered_results)[:6000] if filtered_results else "No IT content found."
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

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:", placeholder="https://...")
    if url_input:
        with st.spinner("Scraping & Filtering..."):
            final_text = scrape_url_with_strict_filter(url_input)
            if "No IT content" in final_text:
                st.warning(final_text)
            else:
                st.success("Scrape complete.")
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        # Grab first 2 and last page to stay under token limits
        pages_to_read = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
        final_text = "".join([reader.pages[i].extract_text() for i in pages_to_read])
        st.success("PDF analyzed successfully.")

if final_text and "Error" not in final_text:
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Simplify for Citizens"):
            ans, dur = query_groq(f"Summarize this bid in 2 sentences: {final_text}", "You are a plain-language expert.")
            st.info(ans)
            if "⚠️" not in ans: st.session_state.total_saved += 5

    with col2:
        if st.button("Extract Technical Specs"):
            ans, dur = query_groq(f"List only IT/Radio equipment found here: {final_text}", "You are a hardware auditor.")
            st.success(ans)
            if "⚠️" not in ans: st.session_state.total_saved += 15

    with col3:
        if st.button("Reporting Guidance"):
            ans, dur = query_groq(f"What are the reporting deadlines? {final_text}", "Compliance officer.")
            st.warning(ans)
            if "⚠️" not in ans: st.session_state.total_saved += 10
