import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Initialize Session States
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def get_driver():
    """Sets up a headless browser for Streamlit Cloud environment."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_dynamic_bids(url):
    """Uses Selenium to wait for RAMPLA/Salesforce to load data."""
    it_keywords = ["software", "hardware", "network", "cabling", "saas", "cloud", "it ", "technology"]
    junk_words = ["detached", "table", "advanced sort", "refresh", "loading"]
    
    driver = get_driver()
    found_bids = []
    
    try:
        driver.get(url)
        # RAMPLA needs time for Salesforce Lightning to render
        time.sleep(6) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        # We look for spans and divs where the text actually lives
        rows = soup.find_all(['span', 'div', 'tr'])
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            
            if any(k in text_lower for k in it_keywords) and not any(j in text_lower for j in junk_words):
                if len(text) > 55:
                    clean_name = text[:110].upper()
                    if clean_name not in [b['name'] for b in found_bids]:
                        found_bids.append({"name": clean_name, "full_text": text})
    finally:
        driver.quit()
    
    return found_bids[:8]

@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    return response.json()['choices'][0]['message']['content']

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

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])
input_container = st.empty()

if st.session_state.active_bid_text is None:
    with input_container.container():
        if input_mode == "Upload PDF":
            uploaded_file = st.file_uploader("Upload PDF", type="pdf", key=f"f_{st.session_state.uploader_key}")
            if uploaded_file:
                reader = PdfReader(uploaded_file)
                st.session_state.active_bid_text = "".join([p.extract_text() for p in reader.pages[:3]])[:6000]
                st.rerun()
        else:
            url_input = st.text_input("Paste Portal URL (Waiting 6s for JS load):")
            if url_input:
                with st.spinner("Opening headless browser to render JavaScript..."):
                    bids = scrape_dynamic_bids(url_input)
                    if bids:
                        for idx, bid in enumerate(bids):
                            with st.container(border=True):
                                st.write(f"### 📦 {bid['name']}")
                                if st.button(f"Analyze This Bid", key=f"b_{idx}"):
                                    st.session_state.active_bid_text = bid['full_text']
                                    st.rerun()
                    else:
                        st.warning("No bids found. If the site has high bot-protection, please use the Upload PDF option.")

# --- 4. DISPLAY ---
if st.session_state.active_bid_text:
    input_container.empty()
    if not st.session_state.summary_ans:
        with st.status("🔍 Analyzing Bid Lifecycle...", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast("Status: Active/Closed/Awarded. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq_fast("Summarize project goal.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq_fast("List IT gear/software.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq_fast("Deadlines and steps.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq_fast("Rules and reporting.", st.session_state.active_bid_text)
            st.session_state.award_ans = query_groq_fast("Winner and amount.", st.session_state.active_bid_text)
            st.session_state.total_saved += 100 
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status: st.success(f"✅ STATUS: {clean_status}")
    else: st.error(f"🚨 STATUS: {clean_status}")

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
