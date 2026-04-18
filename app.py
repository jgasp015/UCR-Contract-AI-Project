import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

# Initialize Session States for Persistant Data
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_link' not in st.session_state: st.session_state.active_bid_link = None

# Storage for the AI responses so they "Stick"
if 'summary_ans' not in st.session_state: st.session_state.summary_ans = None
if 'tech_ans' not in st.session_state: st.session_state.tech_ans = None
if 'submission_ans' not in st.session_state: st.session_state.submission_ans = None
if 'compliance_ans' not in st.session_state: st.session_state.compliance_ans = None

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
st.title("🏛️ Public Sector Contract AI")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    
    if st.button("🔄 Start New Search"):
        # Clear everything
        for key in ['active_bid_text', 'active_bid_link', 'summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans']:
            st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

# --- DATA LOADING PHASE ---
if not st.session_state.active_bid_text:
    if input_mode == "Live Portal Link":
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            with st.spinner("Finding tech bids..."):
                bids = scrape_multi_it_bids(url_input)
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        if st.button(f"Analyze Specific Bid", key=f"btn_{idx}"):
                            st.session_state.active_bid_text = bid['full_text']
                            st.session_state.active_bid_link = bid['link']
                            st.rerun()
    else:
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        manual_url = st.text_input("Paste Source Link for this PDF (Optional):")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]
            st.session_state.active_bid_link = manual_url
            st.rerun()

# --- 4. ANALYSIS AREA (Persistent Tabs) ---
if st.session_state.active_bid_text:
    st.success(f"Analysis Data Loaded.")
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Column 1: Overview
    with col1:
        if st.button("Generate Bid Overview"):
            st.session_state.summary_ans = query_groq(f"Summarize project (Big Picture, Scope, Who Can Apply): {st.session_state.active_bid_text}", "Advisor.")
            st.session_state.total_saved += 10
        
        if st.session_state.summary_ans:
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                st.write(f"**Link:** {st.session_state.active_bid_link}")
                st.write(st.session_state.summary_ans)

    # Column 2: Tech Specs
    with col2:
        if st.button("Extract Tech Specs"):
            st.session_state.tech_ans = query_groq(f"List ONLY IT hardware, cabling, and software: {st.session_state.active_bid_text}", "IT Auditor.")
            st.session_state.total_saved += 20
        
        if st.session_state.tech_ans:
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(st.session_state.tech_ans)

    # Column 3: Submission
    with col3:
        if st.button("Get Submission Info"):
            st.session_state.submission_ans = query_groq(f"Deadlines and how to submit: {st.session_state.active_bid_text}", "Procurement Advisor.")
            st.session_state.total_saved += 15
        
        if st.session_state.submission_ans:
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(st.session_state.submission_ans)

    # Column 4: Compliance
    with col4:
        if st.button("Check Compliance"):
            st.session_state.compliance_ans = query_groq(f"Identify mandatory compliance and reporting rules: {st.session_state.active_bid_text}", "Compliance Auditor.")
            st.session_state.total_saved += 15
        
        if st.session_state.compliance_ans:
            with st.container(border=True):
                st.markdown("#### ⚖️ Compliance Checklist")
                st.write(st.session_state.compliance_ans)
