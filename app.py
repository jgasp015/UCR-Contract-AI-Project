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
    """AI Engine configured for Public Clarity and Professional Accuracy."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Public Communications Liaison for local government. 
                Your job is to make government contracts transparent and easy for citizens to understand.
                
                COMMUNICATION GUIDELINES:
                1. IDENTIFY THE AGENCY: Always state the specific city, county, or state agency involved. Do not use generic terms like 'the government.'
                2. PROFESSIONAL CLARITY: Use simple, professional English. Avoid complex legal jargon (e.g., 'procurement') but also avoid slang (e.g., 'mess up'). 
                3. DIRECTNESS: Use 'failure to meet standards' or 'falling short of requirements' instead of informal terms.
                4. READABILITY: Use short sentences and clear headings. Explain everything as if you are talking to a well-informed neighbor."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: return "The analysis system is currently offline. Please try again shortly."

def scrape_stable_bids(url):
    """Scans portal tables for active business opportunities."""
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
    if st.button("🔄 Start New Search"):
        for k in ['all_bids', 'active_bid_text', 'active_bid_name'] + keys:
            st.session_state[k] = [] if k == 'all_bids' else None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS VIEW ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    st.subheader(f"Document Analysis")
    st.caption(f"Source: {st.session_state.active_bid_name}")
    doc = st.session_state.active_bid_text

    # --- MODE 1: COMPLIANCE & ACCOUNTABILITY MODE ---
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Analyzing Service Standards..."):
                prompt = """
                Provide a factual summary of vendor accountability for this contract. 
                Identify the specific city, county, or state agency involved.
                
                1. SERVICE STANDARDS (Availability): Explain the required uptime percentage and the consequences for the vendor if the service fails.
                2. RESTORATION GOALS (Fixing Issues): Detail how quickly the company must fix problems, specifically referencing different levels of failure (e.g., system-wide vs. single-site).
                3. INSTALLATION TARGETS (Provisioning): Explain the deadlines for setting up services and the penalties for delays.
                4. FINANCIAL PENALTIES: Explain the specific credits or refunds the agency is entitled to if the company fails to meet these requirements.
                5. EXCLUSIONS: Mention the specific 'Stop Clock' reasons why a vendor might not be penalized (e.g., power failure or agency delays).
                """
                st.session_state.report_ans = deep_query(doc, prompt)
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Contract Compliance & Accountability Dashboard")
        st.markdown(st.session_state.report_ans)

    # --- MODE 2: BID DOCUMENTS (STANDARD COMPETITIVE ANALYSIS) ---
    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Scanning Project Details..."):
                st.session_state.detected_due_date = deep_query(doc, "Extract only the deadline date for this bid.")
                st.session_state.summary_ans = deep_query(doc, "Which specific local agency is buying this? Explain the project's purpose and goals in clear, simple English.")
                st.session_state.tech_ans = deep_query(doc, "Describe the technology, software, or equipment being purchased.")
                st.session_state.submission_ans = deep_query(doc, "What specific steps must a business take to apply for this work?")
                st.session_state.compliance_ans = deep_query(doc, "Summarize the legal and insurance requirements for the winning company.")
                st.session_state.award_ans = deep_query(doc, "How will the local agency select a winner? Is there a budget or estimated cost listed?")
                st.session_state.total_saved += 120
                st.rerun()

        st.success(f"✅ Open for Bids (Deadline: {st.session_state.detected_due_date})")
        tabs = st.tabs(["📖 Project Goal", "🛠️ Technology", "📝 Application Steps", "⚖️ Legal Rules", "💰 Selection Process"])
        tabs[0].info(st.session_state.summary_ans)
        tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans)
        tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    st.write("### Found Opportunities")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("View Public Analysis", key=f"bid_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.analysis_mode = "Standard"
                st.rerun()

# --- VIEW 3: INITIAL SEARCH & MULTI-MODE UPLOAD ---
else:
    t1, t2, t3 = st.tabs(["📄 New Project Search", "📊 Performance Standards", "🔗 Search Online"])
    
    with t1:
        st.write("Understand what new projects your local government is planning.")
        up_bid = st.file_uploader("Upload a Bid PDF", type="pdf", key="up_bid")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with t2:
        st.write("See how companies are held accountable for service failures.")
        up_rep = st.file_uploader("Upload a Contract or SOW PDF", type="pdf", key="up_rep")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.active_bid_name = up_rep.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()

    with t3:
        url = st.text_input("Paste Local Government Portal Link:")
        if st.button("Scan for Opportunities"):
            st.session_state.all_bids = scrape_stable_bids(url)
            st.rerun()
