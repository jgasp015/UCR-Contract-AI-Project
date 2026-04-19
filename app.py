import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Persistent Performance Metrics
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# Storage for AI answers
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CACHED AI FUNCTION (Presentation Stability) ---
@st.cache_data(show_spinner=False)
def query_groq_cached(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        data = response.json()
        if "choices" in data:
            return data['choices'][0]['message']['content']
        return f"⚠️ Rate Limit: {data.get('error', {}).get('message', 'Busy')}"
    except:
        return "⚠️ Connection Error"

def scrape_multi_it_bids(url):
    it_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev ", "cabling", "fiber", "saas", "cloud"]
    ignore_words = ["page", "showing", "log out", "reset", "next", "contact us"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all(['tr', 'div', 'li'])
        found_bids = []
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            if any(k in text.lower() for k in it_keywords) and not any(i in text.lower() for i in ignore_words):
                if len(text) > 45:
                    link_tag = row.find('a', href=True)
                    bid_link = urljoin(url, link_tag['href']) if link_tag else url
                    if text[:60] not in [b['name'][:60] for b in found_bids]:
                        found_bids.append({"name": text[:120], "full_text": text, "link": bid_link})
        return found_bids[:10]
    except:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.cache_data.clear()
        for key in ['active_bid_text'] + keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

# --- DATA INPUT SECTION (FIXED) ---
if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input and not st.session_state.active_bid_text:
        with st.spinner("Finding tech bids..."):
            bids = scrape_multi_it_bids(url_input)
            for idx, bid in enumerate(bids):
                with st.container(border=True):
                    st.write(f"### 📦 {bid['name']}")
                    if st.button(f"Analyze Specific Bid", key=f"btn_{idx}"):
                        st.session_state.active_bid_text = bid['full_text']
                        st.rerun()

elif input_mode == "Upload PDF":
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file and not st.session_state.active_bid_text:
        reader = PdfReader(uploaded_file)
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:3000]
        st.rerun()

# --- 4. ANALYSIS AREA ---
if st.session_state.active_bid_text:
    
    if not st.session_state.summary_ans:
        with st.status("🚀 Running Stable Analysis...", expanded=True) as status:
            st.write("Checking Status...")
            st.session_state.status_flag = query_groq_cached(f"Status in 1 word (Active/Awarded/Closed): {st.session_state.active_bid_text}", "Auditor")
            time.sleep(3) 
            
            st.write("Analyzing Overview & Specs...")
            st.session_state.summary_ans = query_groq_cached(f"Summarize goal: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.tech_ans = query_groq_cached(f"List IT gear/cabling: {st.session_state.active_bid_text}", "Auditor")
            time.sleep(3)
            
            st.write("Finalizing Compliance & Submission...")
            st.session_state.submission_ans = query_groq_cached(f"Submission steps: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.compliance_ans = query_groq_cached(f"Compliance & Award info: {st.session_state.active_bid_text}", "Auditor")
            
            st.session_state.total_saved += 80
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    if st.session_state.status_flag and "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    t1, t2, t3, t4 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance & Award"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.write(st.session_state.compliance_ans)
