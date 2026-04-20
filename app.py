import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- 1. SESSION STATE INITIALIZATION ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_name' not in st.session_state: st.session_state.active_bid_name = None
if 'active_bid_url' not in st.session_state: st.session_state.active_bid_url = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'agency_name' not in st.session_state: st.session_state.agency_name = None
if 'project_title' not in st.session_state: st.session_state.project_title = None

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    """AI Engine with strict date-validation and professional persona."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Government Public Information Officer. 
                TODAY'S DATE: April 20, 2026.
                
                STRICT STYLE RULES:
                1. NO GREETINGS: Do not say 'Hello' or 'Hi.'
                2. NO INTROS: Do not repeat agency names or start with filler phrases.
                3. DATE AWARENESS: You are aware today is April 20, 2026. Deadlines before this date are CLOSED.
                4. NO SLANG: Use professional terms like 'failure to meet standards' instead of 'mess up.'
                5. START IMMEDIATELY: Start your response with the facts requested."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: return "Information unavailable."

def scrape_stable_bids(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    blacklist = ["log out", "contact us", "home", "download", "page 1", "records", "reset", "showing 1 to", "continuous", "solicitation number title"]
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(8) 
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        found_bids = []
        for row in soup.find_all('tr'):
            text = row.get_text(separator=' ', strip=True)
            if any(marker in text.lower() for marker in ["rfb-is-", "rfp-", "solicitation"]):
                if not any(bad in text.lower() for bad in blacklist):
                    clean_name = " ".join(text.split())[:150].upper()
                    if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                        found_bids.append({"name": clean_name, "full_text": text, "link": url})
        return found_bids[:10]
    except: return []

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    
    if st.button("🏠 Return Home"):
        for k in ['all_bids', 'active_bid_text', 'active_bid_name', 'agency_name', 'project_title'] + keys:
            st.session_state[k] = [] if k == 'all_bids' else None
        st.rerun()

    if st.button("🔄 Start New Search"):
        for k in ['all_bids', 'active_bid_text', 'active_bid_name', 'agency_name', 'project_title'] + keys:
            st.session_state[k] = [] if k == 'all_bids' else None
        st.rerun()
        
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS VIEW ---
if st.session_state.active_bid_text:
    col_nav, _ = st.columns([1, 4])
    with col_nav:
        if st.button("⬅️ Back to List"):
            st.session_state.active_bid_text = None
            st.rerun()

    doc = st.session_state.active_bid_text

    # STEP 1: SCAN FOR HEADER DATA & STATUS (Once)
    if not st.session_state.agency_name:
        with st.spinner("Analyzing Project Context..."):
            st.session_state.agency_name = deep_query(doc, "Agency name? (e.g. Los Angeles County). ONLY the name.")
            st.session_state.project_title = deep_query(doc, "Official project title? ONLY the title.")
            st.session_state.detected_due_date = deep_query(doc, "Extract only the deadline date (MM/DD/YYYY).")
            
            # Dynamic Status Check
            status_check = deep_query(doc, "Today is April 20, 2026. Is this bid OPEN or CLOSED based on the deadline? Answer ONLY with 'OPEN' or 'CLOSED'.")
            st.session_state.status_flag = "OPEN" if "OPEN" in status_check.upper() else "CLOSED"

    # STEP 2: DISPLAY DYNAMIC HEADER
    if st.session_state.status_flag == "OPEN":
        st.success(f"✅ Open for Bids (Deadline: {st.session_state.detected_due_date})")
    else:
        st.error(f"🚫 Closed (Deadline was: {st.session_state.detected_due_date})")
    
    st.subheader(f"🏛️ {st.session_state.agency_name}")
    st.info(f"**Project:** {st.session_state.project_title}")
    st.caption(f"Source: {st.session_state.active_bid_name}")

    # STEP 3: CONTENT TABS
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Analyzing Service Standards..."):
                prompt = """Summarize service rules. 
                1. RELIABILITY: Operational uptime. 
                2. RESTORATION: Time limits for fixes. 
                3. INSTALLATION: Deadlines and penalties. 
                4. FINANCIALS: Credits for failures.
                DO NOT use greetings or repeat agency name."""
                st.session_state.report_ans = deep_query(doc, prompt)
                st.session_state.total_saved += 60
                st.rerun()
        st.markdown("### 📊 Performance & Accountability Dashboard")
        st.markdown(st.session_state.report_ans)

    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Performing Deep Scan..."):
                st.session_state.summary_ans = deep_query(doc, "Factual summary of project goals. DO NOT include intros or agency name.")
                st.session_state.tech_ans = deep_query(doc, "List required gear/software. Provide only the list.")
                st.session_state.submission_ans = deep_query(doc, "Application steps. Provide only the list.")
                st.session_state.compliance_ans = deep_query(doc, "Insurance/legal rules. START DIRECTLY with rules.")
                st.session_state.award_ans = deep_query(doc, "Selection process and budget. START DIRECTLY with facts.")
                st.session_state.total_saved += 120
                st.rerun()

        tabs = st.tabs(["📖 Project Plan", "🛠️ Technology", "📝 Application Process", "⚖️ Legal Rules", "💰 Winner Selection"])
        tabs[0].info(st.session_state.summary_ans)
        tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans)
        tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    if st.button("⬅️ Back to Search Input"):
        st.session_state.all_bids = []
        st.rerun()
        
    st.write("### Found Opportunities")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("View Public Analysis", key=f"bid_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.analysis_mode = "Standard"
                st.rerun()

# --- VIEW 3: INITIAL SEARCH ---
else:
    t1, t2, t3 = st.tabs(["📄 New Project Search", "📊 Performance Standards", "🔗 Search Online"])
    
    with t1:
        up_bid = st.file_uploader("Upload a Bid PDF", type="pdf", key="up_bid")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with t2:
        up_rep = st.file_uploader("Upload a Contract/SOW PDF", type="pdf", key="up_rep")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.active_bid_name = up_rep.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()

    with t3:
        url = st.text_input("Paste Portal Link:")
        if st.button("Scan for Opportunities"):
            st.session_state.all_bids = scrape_stable_bids(url)
            st.rerun()
