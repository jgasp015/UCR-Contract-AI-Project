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
    st.error("🔑 API Key missing!")
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
        "temperature": 0.0 # Lowest temperature for maximum facts/zero creativity
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()
        duration = round(time.time() - start_time, 2)
        return data['choices'][0]['message']['content'], duration
    except:
        return "⚠️ Error connecting to AI.", 0

def scrape_url_with_strict_filter(url):
    """Targets Chicago and LA portals specifically."""
    it_keywords = ["computer", "software", "network", "telecommunication", "server", "technology", "it hardware"]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # We look for table rows specifically
        rows = soup.find_all(['tr', 'p', 'li'])
        filtered_results = []
        
        for row in rows:
            text = row.get_text(strip=True)
            # STRICKER FILTER: Only keep the row if it hits an IT keyword
            if any(key in text.lower() for key in it_keywords):
                filtered_results.append(text)
        
        return " ".join(filtered_results)[:7000] if filtered_results else "No IT content found."
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Simplifier")

with st.sidebar:
    st.header("Project Performance")
    if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])
final_text = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Filtering for IT content..."):
            final_text = scrape_url_with_strict_filter(url_input)
            st.success("Scrape complete.")
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        final_text = "".join([p.extract_text() for p in reader.pages[:3]])

if final_text:
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Simplify for Citizens"):
            role = "You are a plain-language expert."
            prompt = f"IF this text is about IT, summarize it. IF NOT, say 'This is not an IT contract.' Text: {final_text}"
            ans, dur = query_groq(prompt, role)
            st.info(ans)
            st.session_state.total_saved += 5

    with col2:
        if st.button("Extract Technical Specs"):
            # THE KEY FIX: Highlighting that we only want COMPUTERS/SOFTWARE
            role = "You are a hardware auditor. You ONLY extract Information Technology equipment."
            prompt = (
                f"Strict Instruction: Review the text. If you see fire hoses, grease, oils, or construction materials, IGNORE THEM. "
                f"ONLY list computers, servers, software, and networking gear. If none found, say 'No IT Hardware detected'. "
                f"Text: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            st.success(ans)
            st.session_state.total_saved += 15

    with col3:
        if st.button("Reporting Guidance"):
            role = "Compliance officer."
            prompt = f"Identify reporting deadlines for this IT project: {final_text}"
            ans, dur = query_groq(prompt, role)
            st.warning(ans)
            st.session_state.total_saved += 10
