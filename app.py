import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Initialize Session States
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return response.json()['choices'][0]['message']['content']
    except:
        return "⚠️ AI Error"

def scrape_stable_bids(url):
    it_keywords = ["software", "hardware", "network", "cabling", "saas", "cloud", "it ", "technology", "telecom"]
    junk_words = ["javascript", "detached", "loading", "refresh", "page 1 of", "items per page", "reset showing"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        found_bids = []
        for row in soup.find_all(['tr', 'div']):
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            if len(text) > 55 and any(k in text_lower for k in it_keywords) and not any(j in text_lower for j in junk_words):
                clean_name = " ".join(text.split())[:115].upper()
                link_tag = row.find('a', href=True)
                bid_link = urljoin(url, link_tag['href']) if link_tag else url
                if clean_name[:60] not in [b['name'][:60] for b in found_bids]:
                    found_bids.append({"name": clean_name, "full_text": text, "link": bid_link})
        return found_bids[:10]
    except:
        return []

# --- 3. UI LAYOUT ---
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
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])
input_placeholder = st.empty()

if st.session_state.active_bid_text is None:
    with input_placeholder.container():
        if input_mode == "Upload PDF":
            uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.uploader_key}")
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                total_pages = len(reader.pages)
                
                # RECOVERY LOGIC: Scan first 2 pages AND last 5 pages (where price sheets hide)
                # This ensures Nlyte requirements on Page 24 are captured.
                important_pages = [0, 1] + list(range(max(2, total_pages - 6), total_pages))
                
                text_extract = ""
                for i in important_pages:
                    try:
                        text_extract += reader.pages[i].extract_text() + "\n"
                    except: continue
                
                st.session_state.active_bid_text = text_extract[:12000] # Higher token limit
                st.rerun()
        else:
            url_input = st.text_input("Paste Portal URL:")
            if url_input:
                bids = scrape_stable_bids(url_input)
                if bids:
                    for idx, bid in enumerate(bids):
                        with st.container(border=True):
                            st.write(f"### 📦 {bid['name']}")
                            if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                                st.session_state.active_bid_text = bid['full_text']
                                st.rerun()

# --- 4. ANALYSIS & DISPLAY ---
if st.session_state.active_bid_text:
    input_placeholder.empty()
    if not st.session_state.summary_ans:
        with st.status("🔍 Performing Lifecycle Audit...", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast("Identify status: Active, Closed, or Awarded. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq_fast("Summarize project goal/scope.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq_fast("List all IT hardware, software, and cabling requirements.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq_fast("Identify deadlines and submission requirements.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq_fast("Identify mandatory insurance and compliance rules.", st.session_state.active_bid_text)
            st.session_state.award_ans = query_groq_fast("Identify awarded vendor or estimate budget.", st.session_state.active_bid_text)
            st.session_state.total_saved += 100 
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status: st.success(f"✅ STATUS: {clean_status}")
    else: st.error(f"🚨 STATUS: {clean_status}")

    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
