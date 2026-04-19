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

# --- 1. SAFE INITIALIZATION (Fixes the AttributeError) ---
# This block MUST come before any 'if st.session_state' checks
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_name' not in st.session_state: st.session_state.active_bid_name = None
if 'active_bid_url' not in st.session_state: st.session_state.active_bid_url = None
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'detected_due_date' not in st.session_state: st.session_state.detected_due_date = "N/A"

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

# Create a temporary directory for downloads
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
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a concise procurement expert."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    if max_tokens: payload["max_tokens"] = max_tokens
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except:
        return "N/A"

def scrape_stable_bids(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
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
                clean_name = " ".join(text.split())[:150].upper()
                if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                    found_bids.append({
                        "name": clean_name, 
                        "full_text": text, 
                        "link": url  # In LA County, the main list URL is the anchor
                    })
        return found_bids[:10]
    except:
        return []

def fetch_document_binary(url):
    """Clicks Download and grabs file from the LA County Portal."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    prefs = {"download.default_directory": DOWNLOAD_DIR}
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(5)
        # Try to find the specific blue Download button
        btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Download')] | //a[contains(@class, 'btn')]")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(8)
        files = os.listdir(DOWNLOAD_DIR)
        if files:
            file_path = os.path.join(DOWNLOAD_DIR, files[0])
            with open(file_path, "rb") as f: data = f.read()
            os.remove(file_path)
            return data, files[0]
        return None, None
    finally:
        driver.quit()

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 New Search"):
        # Reset everything
        for k in ['all_bids', 'active_bid_text', 'active_bid_name', 'active_bid_url', 'detected_due_date'] + keys:
            if k == 'all_bids': st.session_state[k] = []
            elif k == 'total_saved': pass
            else: st.session_state[k] = None
        st.rerun()

# --- VIEW 1: ANALYSIS ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to List"):
        st.session_state.active_bid_text = None
        st.rerun()

    st.subheader(f"Analyzing: {st.session_state.active_bid_name}")

    if st.button("📥 Pull & Download Original Doc to My Site"):
        with st.spinner("Grabbing file from portal..."):
            b, name = fetch_document_binary(st.session_state.active_bid_url or "https://camisvr.co.la.ca.us/LACoBids/")
            if b:
                st.download_button(label=f"Click to Download {name}", data=b, file_name=name)
            else:
                st.error("Portal requires manual document download.")

    if not st.session_state.summary_ans:
        with st.status("🚀 Analyzing...") as status:
            doc = st.session_state.active_bid_text
            st.session_state.detected_due_date = deep_query(doc, "Due Date? (e.g. April 24, 2026)", max_tokens=15)
            st.session_state.status_flag = "OPEN"
            st.session_state.summary_ans = deep_query(doc, "Summarize goal/scope.")
            st.session_state.tech_ans = deep_query(doc, "List tech requirements.")
            st.session_state.submission_ans = deep_query(doc, "Submission steps.")
            st.session_state.compliance_ans = deep_query(doc, "Legal/Insurance.")
            st.session_state.award_ans = deep_query(doc, "Award/Budget info.")
            st.session_state.total_saved += 150
            st.rerun()

    st.success(f"✅ STATUS: OPEN (Due: {st.session_state.detected_due_date})")
    tabs = st.tabs(["Overview", "Tech Specs", "Submission", "Compliance", "Award"])
    tabs[0].info(st.session_state.summary_ans)
    tabs[1].success(st.session_state.tech_ans)
    tabs[2].warning(st.session_state.submission_ans)
    tabs[3].error(st.session_state.compliance_ans)
    tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    st.write(f"Found {len(st.session_state.all_bids)} results:")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze Bid", key=f"btn_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.active_bid_url = bid['link']
                st.rerun()

# --- VIEW 3: INITIAL SEARCH ---
else:
    mode = st.radio("Source:", ["Upload PDF", "Live Portal Link"])
    if mode == "Upload PDF":
        up = st.file_uploader("Upload PDF", type="pdf")
        if up:
            pdf = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in pdf.pages])
            st.session_state.active_bid_name = up.name
            st.rerun()
    else:
        url = st.text_input("Portal URL:")
        if st.button("Scrape"):
            with st.spinner("Searching..."):
                st.session_state.all_bids = scrape_stable_bids(url)
                st.rerun()
