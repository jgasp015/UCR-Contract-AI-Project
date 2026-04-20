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
# Safely initializes all variables to prevent AttributeError [cite: 1043]
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
    """AI Engine configured for high-precision contract and SLA analysis."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are an expert Contract Compliance Analyst. You specialize in technical triggers, SLA objectives, and SOW auditing. Provide audit-ready data."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except: return "Analysis currently unavailable."

def scrape_stable_bids(url):
    """Scrapes portal tables and filters out headers/junk to show only active opportunities."""
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
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            if any(marker in text.lower() for marker in ["rfb-is-", "rfp-", "solicitation"]):
                if not any(bad in text.lower() for bad in blacklist):
                    clean_name = " ".join(text.split())[:150].upper()
                    if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                        found_bids.append({"name": clean_name, "full_text": text, "link": url})
        return found_bids[:10]
    except: return []

def fetch_document_binary(url):
    """Attempts to automate the portal download click and retrieve the binary file."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    prefs = {"download.default_directory": DOWNLOAD_DIR}
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(6)
        selectors = ["//button[contains(text(), 'Download')]", "//a[contains(text(), 'Download')]", "//a[contains(@class, 'btn-primary')]"]
        btn = None
        for s in selectors:
            try:
                btn = driver.find_element(By.XPATH, s)
                if btn: break
            except: continue
        if btn:
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(10)
            files = os.listdir(DOWNLOAD_DIR)
            if files:
                file_path = os.path.join(DOWNLOAD_DIR, files[0])
                with open(file_path, "rb") as f: data = f.read()
                os.remove(file_path)
                return data, files[0]
        return None, None
    except: return None, None
    finally: driver.quit()

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

    st.subheader(f"Analyzing Document")
    st.caption(st.session_state.active_bid_name)
    doc = st.session_state.active_bid_text

    # --- MODE 1: COMPLIANCE & REPORTING MODE ---
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Extracting Technical Qualifiers & SLA Triggers..."):
                prompt = """
                As an expert Contract Compliance Analyst, extract the technical reporting 
                guidelines and SLA triggers from this document.
                
                1. TECHNICAL QUALIFIERS: Explain exactly what triggers a penalty. 
                   - Define metrics for Availability, Excessive Outages, and Catastrophic Outages.
                   - Explain the specific time thresholds (e.g., '> X minutes') that trigger remediation.
                
                2. PERFORMANCE METRICS TABLE: Create a markdown table showing:
                   - SLA Name
                   - Performance Objective (The committed threshold)
                   - Remediation (Credits or liquidated damages if missed)
                
                3. AUDIT NOTES: List the specific 'Stop Clock Conditions' that allow 
                   the vendor to pause the outage timer.
                """
                st.session_state.report_ans = deep_query(doc, prompt)
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Contract Compliance & SLA Dashboard")
        st.markdown(st.session_state.report_ans)

    # --- MODE 2: BID DOCUMENTS (STANDARD COMPETITIVE ANALYSIS) ---
    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Scanning Competitive Bid Details..."):
                st.session_state.detected_due_date = deep_query(doc, "Today is April 20, 2026. Extract ONLY the bid due date.")
                st.session_state.summary_ans = deep_query(doc, "Summarize the project goal and technical scope.")
                st.session_state.tech_ans = deep_query(doc, "List IT requirements, software, and hardware.")
                st.session_state.submission_ans = deep_query(doc, "List submission steps and mandatory documents.")
                st.session_state.compliance_ans = deep_query(doc, "Identify insurance and legal requirements.")
                st.session_state.award_ans = deep_query(doc, "Identify award criteria or budget information.")
                st.session_state.total_saved += 120
                st.rerun()

        st.success(f"✅ STATUS: OPEN (Due: {st.session_state.detected_due_date})")
        tabs = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award"])
        tabs[0].info(st.session_state.summary_ans)
        tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans)
        tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze as Bid Document", key=f"bid_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.analysis_mode = "Standard"
                st.rerun()

# --- VIEW 3: INITIAL SEARCH & MULTI-MODE UPLOAD ---
else:
    t1, t2, t3 = st.tabs(["📄 Upload Bid Doc", "📊 Upload SOW/Reporting Doc", "🔗 Live Portal Link"])
    
    with t1:
        st.write("Extract competitive intelligence for new bid opportunities.")
        up_bid = st.file_uploader("Upload Bid PDF", type="pdf", key="up_bid")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with t2:
        st.write("Extract technical qualifiers and SLA triggers for monthly reporting.")
        up_rep = st.file_uploader("Upload SOW or Compliance Doc", type="pdf", key="up_rep")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.active_bid_name = up_rep.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()

    with t3:
        url = st.text_input("Paste Portal URL:")
        if st.button("Scrape & Cherry-Pick Bids"):
            st.session_state.all_bids = scrape_stable_bids(url)
            st.rerun()
