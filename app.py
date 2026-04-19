import streamlit as st
import requests
import time
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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
        return "Analysis error."

def scrape_stable_bids(url):
    """Refined scraper that targets table rows (LA County style)."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    blacklist = ["log out", "contact us", "home", "download a list", "page 1", "items per page", "records", "reset", "showing 1 to", "powered by", "download a csv"]

    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(8) # Increased wait for LA County's slow table load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        found_bids = []
        
        # Target table rows specifically to get Solicitation IDs and Titles
        rows = soup.find_all('tr')
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            text_lower = text.lower()
            
            # Look for the RFB/RFP markers seen in your screenshot
            if any(marker in text_lower for marker in ["rfb-is-", "rfp-", "solicitation"]):
                if not any(bad in text_lower for bad in blacklist):
                    # Clean up the text to make a nice title
                    clean_name = " ".join(text.split())[:150].upper()
                    
                    if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                        found_bids.append({
                            "name": clean_name, 
                            "full_text": f"BID DATA: {text}", 
                            "link": url
                        })
        
        # If no table rows found, fallback to links
        if not found_bids:
            for link in soup.find_all('a', href=True):
                text = link.get_text(strip=True)
                if len(text) > 30 and not any(bad in text.lower() for bad in blacklist):
                    found_bids.append({"name": text.upper(), "full_text": text, "link": urljoin(url, link['href'])})

        return found_bids[:10]
    except Exception as e:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.session_state.active_bid_text = None
        st.session_state.uploader_key += 1
        for key in keys: st.session_state[key] = None
        st.rerun()

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])

if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.uploader_key}")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])[:45000]
            st.rerun()
    else:
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            with st.spinner("🕵️ Searching table for RFPs and RFBs..."):
                bids = scrape_stable_bids(url_input)
            if bids:
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                            st.session_state.active_bid_text = bid['full_text']
                            st.rerun()
            else:
                st.error("Could not find bids in the table. The site may be protected. Try 'Upload PDF'.")

# --- 4. ANALYSIS & DISPLAY ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🚀 Analyzing Contract...") as status:
            doc = st.session_state.active_bid_text
            st.session_state.status_flag = deep_query(doc, "Status: OPEN, ACTIVE, CLOSED, or AWARDED? ONE WORD ONLY.", max_tokens=10)
            st.session_state.summary_ans = deep_query(doc, "Summarize goal and scope.")
            st.session_state.tech_ans = deep_query(doc, "List IT/software/tech requirements.")
            st.session_state.submission_ans = deep_query(doc, "Identify due dates.")
            st.session_state.compliance_ans = deep_query(doc, "Identify insurance/legal.")
            st.session_state.award_ans = deep_query(doc, "Identify awarded vendor or budget.")
            st.session_state.total_saved += 150
            st.rerun()

    clean_status = str(st.session_state.status_flag).strip().upper().replace(".", "")
    if any(word in clean_status for word in ["OPEN", "ACTIVE"]):
        st.success(f"✅ STATUS: {clean_status}")
    elif "AWARDED" in clean_status:
        st.info(f"💰 STATUS: {clean_status}")
    else:
        st.error(f"🚨 STATUS: {clean_status}")

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
