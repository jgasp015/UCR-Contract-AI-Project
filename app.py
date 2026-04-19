import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except:
        return "⚠️ AI Error"

def scrape_multi_it_bids(url):
    """Highly filtered scraper to remove 'behind the scenes' technical text."""
    # MUST contain one of these
    it_keywords = ["software", "hardware", "network", "cabling", "saas", "cloud", "telecom", "it ", "technology", "computer", "fiber", "protective"]
    
    # MUST NOT contain any of these (Technical 'Behind the scenes' junk)
    junk_words = [
        "detached", "table", "advanced sort", "refresh", "loading", "javascript", 
        "navigation", "login", "attach", "detach", "more...", "next", "items per page",
        "specification number", "event program", "abstracts status"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Focus on rows and divs likely to be actual content
        rows = soup.find_all(['tr', 'div', 'li'])
        found_bids = []
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            
            # 1. Check if it has an IT keyword
            # 2. Check if it's NOT junk
            # 3. Ensure it's not just a single word
            if any(k in text_lower for k in it_keywords) and not any(j in text_lower for j in junk_words):
                if len(text) > 40:
                    link_tag = row.find('a', href=True)
                    bid_link = urljoin(url, link_tag['href']) if link_tag else url
                    
                    # Prevent duplicates
                    if text[:50].upper() not in [b['name'][:50] for b in found_bids]:
                        found_bids.append({"name": text[:120].upper(), "full_text": text, "link": bid_link})
        
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
        st.session_state.active_bid_text = None
        st.session_state.uploader_key += 1
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])
input_container = st.empty()

if st.session_state.active_bid_text is None:
    with input_container.container():
        if input_mode == "Upload PDF":
            uploaded_file = st.file_uploader("Upload PDF", type="pdf", key=f"file_up_{st.session_state.uploader_key}")
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
                st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:6000]
                st.rerun()
        else:
            url_input = st.text_input("Paste Portal URL:")
            if url_input:
                with st.spinner("Filtering for real bids..."):
                    bids = scrape_multi_it_bids(url_input)
                    if bids:
                        for idx, bid in enumerate(bids):
                            with st.container(border=True):
                                st.write(f"### 📦 {bid['name']}")
                                if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                                    st.session_state.active_bid_text = bid['full_text']
                                    st.rerun()
                    else:
                        st.warning("No matching bids found. Please try a different URL or Upload PDF.")

# --- 4. ANALYSIS ---
if st.session_state.active_bid_text:
    input_container.empty()
    if not st.session_state.summary_ans:
        with st.status("🔍 Analyzing Bid Details...", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast("Status: Active, Closed, or Awarded. 1 word.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.summary_ans = query_groq_fast("Summarize project goal.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.tech_ans = query_groq_fast("List IT hardware/software/cabling.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.submission_ans = query_groq_fast("Deadlines and submission steps.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.compliance_ans = query_groq_fast("Mandatory rules/reporting.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.award_ans = query_groq_fast("Winner and amount.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.total_saved += 100 
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status: st.success(f"✅ STATUS: {clean_status}")
    elif "AWARDED" in clean_status: st.info(f"💰 STATUS: {clean_status}")
    else: st.error(f"🚨 STATUS: {clean_status}")

    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
