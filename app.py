import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

if 'total_saved' not in st.session_state: 
    st.session_state.total_saved = 0

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        data = response.json()
        return data['choices'][0]['message']['content'] if "choices" in data else "⚠️ AI Busy"
    except:
        return "⚠️ Connection Error"

def scrape_multi_it_bids(url):
    """Refined scraper that ignores navigation and page numbers."""
    it_keywords = [
        "computer", "software", "network", "telecommunication", "hardware", 
        "radio", "data", "ev ", "cabling", "fiber", "saas", "cloud", "technology"
    ]
    # Navigation words we want to EXCLUDE
    ignore_words = ["page", "showing", "items per page", "log out", "reset", "next", "previous", "contact us"]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all(['tr', 'div', 'li', 'span'])
        found_bids = []
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            
            # CHECK 1: Must have an IT keyword
            # CHECK 2: Must NOT have navigation words (like 'Page 3 of 3')
            if any(k in text_lower for k in it_keywords) and not any(i in text_lower for i in ignore_words):
                if len(text) > 45: # Ignore small buttons/labels
                    link_tag = row.find('a', href=True)
                    bid_link = urljoin(url, link_tag['href']) if link_tag else url
                    if text[:60] not in [b['name'][:60] for b in found_bids]:
                        found_bids.append({"name": text[:100], "full_text": text, "link": bid_link})
        return found_bids[:12]
    except:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""
manual_url = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Filtering for technology bids..."):
            bids = scrape_multi_it_bids(url_input)
            if bids:
                # Track index to create unique button keys
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        st.markdown(f"🔗 [Direct Link]({bid['link']})")
                        # UNIQUE KEY: bid['name'] + idx prevents the crash
                        if st.button("Deep Analyze This Bid Row", key=f"btn_{idx}"):
                            final_text = bid['full_text']
                            manual_url = bid['link']
            else:
                st.warning("No IT bids found. Navigation items (Page numbers, Log out) were hidden.")

else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    manual_url = st.text_input("Paste Source Link for this PDF (Optional):")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]

# --- ANALYSIS BUTTONS ---
if final_text:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Bid Overview"):
            ans = query_groq(f"Summarize in simple sections (The Big Picture, Technical Scope, Who Can Apply): {final_text}", "Advisor.")
            st.info(ans)
            st.session_state.total_saved += 10
    with col2:
        if st.button("Technical Specs"):
            ans = query_groq(f"List ONLY the IT hardware/cabling: {final_text}", "Auditor.")
            st.success(ans)
            st.session_state.total_saved += 20
    with col3:
        if st.button("Bid Submission"):
            ans = query_groq(f"Deadlines and submission steps: {final_text}", "Advisor.")
            st.warning(ans)
            st.session_state.total_saved += 15
    with col4:
        if st.button("Compliance Requirements"):
            ans = query_groq(f"Insurance and reporting duties: {final_text}", "Auditor.")
            st.error(ans)
            st.session_state.total_saved += 15
