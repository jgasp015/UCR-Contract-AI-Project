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
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'detected_due_date' not in st.session_state: st.session_state.detected_due_date = "N/A"
if 'show_manual_hint' not in st.session_state: st.session_state.show_manual_hint = False

# Analytical keys including the new reporting tab
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag', 'report_ans']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, max_tokens=None):
    """Llama 3.1 Analysis Engine configured for Senior Analyst output."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a senior CALNET Reporting Analyst. You simplify complex SLA and procurement data into clear snapshots for monthly reconciliation."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    if max_tokens: payload["max_tokens"] = max_tokens
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except:
        return "Analysis currently unavailable."

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
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            if any(marker in text_lower for marker in ["rfb-is-", "rfp-", "solicitation"]):
                if not any(bad in text_lower for bad in blacklist):
                    clean_name = " ".join(text.split())[:150].upper()
                    if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                        found_bids.append({"name": clean_name, "full_text": text, "link": url})
        return found_bids[:10]
    except:
        return []

def fetch_document_binary(url):
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
    if st.button("🔄 New Search"):
        st.session_state.all_bids = []
        st.session_state.active_bid_text = None
        st.session_state.active_bid_name = None
        st.session_state.show_manual_hint = False
        st.session_state.detected_due_date = "N/A"
        for k in keys: st.session_state[k] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to Search Results"):
        st.session_state.active_bid_text = None
        st.session_state.show_manual_hint = False
        for k in keys: st.session_state[k] = None
        st.rerun()

    st.subheader(f"Analyzing Bid Opportunity")
    st.info(st.session_state.active_bid_name)

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚀 Pull Original Doc to Analyzer"):
            with st.spinner("Bypassing portal security..."):
                b, name = fetch_document_binary(st.session_state.active_bid_url or "https://camisvr.co.la.ca.us/LACoBids/")
                if b:
                    st.download_button(label=f"📥 Download {name} from My Site", data=b, file_name=name)
                else:
                    st.session_state.show_manual_hint = True
    with col2:
        if st.session_state.active_bid_url:
            st.link_button("🔗 Open Portal Download Page", st.session_state.active_bid_url, type="primary")

    if st.session_state.show_manual_hint:
        st.warning("💡 **Portal Restriction:** Use the blue button above to download manually, then 'Upload PDF' to re-analyze.")

    # --- AUTO-ANALYSIS TRIGGER ---
    if not st.session_state.summary_ans:
        with st.status("🚀 Performing Deep Scan & Reporting Analysis...") as status:
            doc = st.session_state.active_bid_text
            
            # Metadata extraction
            st.session_state.detected_due_date = deep_query(doc, "Today is April 19, 2026. Extract ONLY the bid due date.", max_tokens=15)
            st.session_state.status_flag = "OPEN"
            
            # Standard tabs
            st.session_state.summary_ans = deep_query(doc, "Summarize goal and scope.")
            st.session_state.tech_ans = deep_query(doc, "List IT requirements.")
            st.session_state.submission_ans = deep_query(doc, "Identify submission steps.")
            st.session_state.compliance_ans = deep_query(doc, "Identify insurance/legal.")
            st.session_state.award_ans = deep_query(doc, "Identify awarded vendor.")
            
            # --- MANDATORY REPORTING TAB ANALYSIS ---
            reporting_prompt = """
            As a Senior Reporting Analyst, extract the SLA Reporting requirements from this document. 
            Focus specifically on:
            1. Availability Objectives (percentages). [cite: 1087]
            2. Restoral Objectives for CAT 2, CAT 3, and Service Outages (time limits). [cite: 1116, 1142, 1153]
            3. Provisioning Objectives 1 and 2. [cite: 1188]
            4. Penalties/Credits associated with these metrics. [cite: 1094, 1119, 1145, 1154, 1189]
            Present this as a clean, simple markdown table for a monthly reconciliation report.
            """
            st.session_state.report_ans = deep_query(doc, reporting_prompt)
            
            st.session_state.total_saved += 150
            st.rerun()

    st.success(f"✅ STATUS: OPEN (Due: {st.session_state.detected_due_date})")
    
    # Display tabs including the requested Reporting Process
    tabs = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award", "📊 Reporting Process"])
    tabs[0].info(st.session_state.summary_ans)
    tabs[1].success(st.session_state.tech_ans)
    tabs[2].warning(st.session_state.submission_ans)
    tabs[3].error(st.session_state.compliance_ans)
    tabs[4].write(st.session_state.award_ans)
    tabs[5].markdown(st.session_state.report_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    st.write(f"Found {len(st.session_state.all_bids)} bid opportunities:")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze Bid Details", key=f"btn_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.active_bid_url = bid['link']
                st.rerun()

# --- VIEW 3: INITIAL SEARCH / PDF UPLOAD ---
else:
    mode = st.radio("Source:", ["Upload PDF", "Live Portal Link"])
    if mode == "Upload PDF":
        up = st.file_uploader("Upload Bid PDF for Analysis", type="pdf")
        if up:
            pdf = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in pdf.pages])
            st.session_state.active_bid_name = up.name
            st.rerun()
    else:
        url = st.text_input("Paste Portal URL:", placeholder="https://camisvr.co.la.ca.us/...")
        if st.button("Scrape Bids"):
            with st.spinner("Filtering for IT-related bids..."):
                st.session_state.all_bids = scrape_stable_bids(url)
                st.rerun()
