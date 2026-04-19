import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Initialize Session States to keep the UI stable
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

# Analysis Persistence Keys
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Please add GROQ_API_KEY to your Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. STABLE & FAST FUNCTIONS ---

@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    """Leverages Paid Tier for high-speed, multi-tab analysis."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ AI Analysis Error: {str(e)}"

def scrape_stable_bids(url):
    """Reliable scraper with a 15-second timeout for slower portals."""
    it_keywords = ["software", "hardware", "network", "cabling", "saas", "cloud", "it ", "technology", "telecom"]
    junk_words = ["javascript", "detached", "loading", "refresh", "login", "advanced sort", "table"]
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    
    try:
        # TIMEOUT ADDITION: Increased to 15s for better portal reach
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        found_bids = []
        
        # Scan common content containers
        for row in soup.find_all(['tr', 'div', 'li', 'span']):
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            
            # Check for Technology Keywords and filter out 'behind the scenes' technical junk
            if any(k in text_lower for k in it_keywords) and not any(j in text_lower for j in junk_words):
                if len(text) > 45:
                    clean_name = text[:110].upper()
                    # Link recovery
                    link_tag = row.find('a', href=True)
                    bid_link = urljoin(url, link_tag['href']) if link_tag else url
                    
                    if clean_name not in [b['name'] for b in found_bids]:
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
        st.session_state.uploader_key += 1 # Forces file uploader to refresh
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])
input_placeholder = st.empty()

# --- INPUT PROCESSING ---
if st.session_state.active_bid_text is None:
    with input_placeholder.container():
        if input_mode == "Upload PDF":
            # Dynamic key ensures the widget resets correctly on 'New Search'
            uploaded_file = st.file_uploader(
                "Upload Bid Document (PDF)", 
                type="pdf", 
                key=f"pdf_up_{st.session_state.uploader_key}"
            )
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                # Read first 3 pages for context (Paid Tier can handle more)
                text_extract = "".join([p.extract_text() for p in reader.pages[:3]])
                st.session_state.active_bid_text = text_extract[:7000]
                st.rerun()
        
        else:
            url_input = st.text_input("Paste Portal URL:", placeholder="https://...")
            if url_input:
                with st.spinner("Filtering for Technology Bids..."):
                    bids = scrape_stable_bids(url_input)
                    if bids:
                        for idx, bid in enumerate(bids):
                            with st.container(border=True):
                                st.write(f"### 📦 {bid['name']}")
                                if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                                    st.session_state.active_bid_text = bid['full_text']
                                    st.rerun()
                    else:
                        st.warning("No bids found. Note: JavaScript-only portals must be analyzed via 'Upload PDF' mode.")

# --- 4. LIFECYCLE ANALYSIS ---
if st.session_state.active_bid_text:
    # Clear the input area to focus on results
    input_placeholder.empty()
    
    if not st.session_state.summary_ans:
        with st.status("🔍 Performing Full Lifecycle Audit...", expanded=True) as status:
            # All calls execute back-to-back using Paid Tier speed
            st.session_state.status_flag = query_groq_fast("Identify status: Active, Closed, or Awarded. 1 word only.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.summary_ans = query_groq_fast("Summarize project goal and scope.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.tech_ans = query_groq_fast("List all IT hardware, software, and cabling requirements.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.submission_ans = query_groq_fast("Identify all deadlines and submission requirements.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.compliance_ans = query_groq_fast("Identify mandatory compliance, insurance, and reporting rules.", f"Text: {st.session_state.active_bid_text}")
            st.session_state.award_ans = query_groq_fast("Identify the Awarded Vendor and Contract Amount. If none, estimate the budget.", f"Text: {st.session_state.active_bid_text}")
            
            st.session_state.total_saved += 100 
            status.update(label="Analysis Complete", state="complete", expanded=False)
            st.rerun()

    # --- FINAL DISPLAY ---
    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status:
        st.success(f"✅ STATUS: {clean_status}")
    elif "AWARDED" in clean_status:
        st.info(f"💰 STATUS: {clean_status}")
    else:
        st.error(f"🚨 STATUS: {clean_status}")

    st.divider()
    
    # Professional 5-Tab Interface
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    
    with t1:
        st.info(st.session_state.summary_ans)
    with t2:
        st.success(st.session_state.tech_ans)
    with t3:
        st.warning(st.session_state.submission_ans)
    with t4:
        st.error(st.session_state.compliance_ans)
    with t5:
        st.write(st.session_state.award_ans)
