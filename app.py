import streamlit as st
import requests
import time
from io import BytesIO
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- 1. SESSION STATE INITIALIZATION ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_name' not in st.session_state: st.session_state.active_bid_name = None
if 'active_bid_url' not in st.session_state: st.session_state.active_bid_url = None
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'detected_due_date' not in st.session_state: st.session_state.detected_due_date = "N/A"

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
        return "N/A"

def scrape_stable_bids(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    blacklist = ["log out", "contact us", "home", "download", "page 1", "records", "reset", "showing 1 to", "powered by"]

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
                    # Try to find a PDF link in the row
                    doc_link = row.find('a', href=lambda x: x and ('.pdf' in x or 'download' in x))
                    full_doc_url = urljoin(url, doc_link['href']) if doc_link else None
                    
                    if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                        found_bids.append({
                            "name": clean_name, 
                            "full_text": text, 
                            "doc_url": full_doc_url
                        })
        return found_bids[:10]
    except:
        return []

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 New Search"):
        for key in keys + ['all_bids', 'active_bid_text', 'active_bid_name', 'active_bid_url']:
            st.session_state[key] = None if key in keys else ([] if key == 'all_bids' else None)
        st.rerun()

# VIEW 1: Analysis View
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to Search Results"):
        st.session_state.active_bid_text = None
        for key in keys: st.session_state[key] = None
        st.rerun()

    st.subheader(f"Analyzing: {st.session_state.active_bid_name}")
    
    # --- DOWNLOAD BUTTON ---
    if st.session_state.active_bid_url:
        try:
            file_res = requests.get(st.session_state.active_bid_url, timeout=10)
            st.download_button(label="📥 Download Original Bid Document", data=file_res.content, file_name="bid_doc.pdf")
        except:
            st.caption("Direct download link unavailable for this bid.")

    # --- AI ANALYSIS ---
    if not st.session_state.summary_ans:
        with st.status("🚀 Running Deep Scan...") as status:
            doc = st.session_state.active_bid_text
            st.session_state.detected_due_date = deep_query(doc, "Extract ONLY the bid due date.", max_tokens=15)
            st.session_state.status_flag = "OPEN" # Force open for your current testing
            st.session_state.summary_ans = deep_query(doc, "Summarize goal and scope.")
            st.session_state.tech_ans = deep_query(doc, "List IT requirements.")
            st.session_state.submission_ans = deep_query(doc, "Identify submission steps.")
            st.session_state.compliance_ans = deep_query(doc, "Identify insurance/legal.")
            st.session_state.award_ans = deep_query(doc, "Identify award info.")
            st.session_state.total_saved += 150
            st.rerun()

    # Restoration of Status Badges
    st.success(f"✅ STATUS: OPEN (Due: {st.session_state.detected_due_date})")
    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)

# VIEW 2: Search Results
elif st.session_state.all_bids:
    st.write(f"Found {len(st.session_state.all_bids)} bid opportunities:")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze Bid Details", key=f"btn_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.active_bid_url = bid['doc_url']
                st.rerun()

# VIEW 3: Initial Search & PDF Upload
else:
    input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])[:45000]
            st.session_state.active_bid_name = uploaded_file.name
            st.rerun()
    else:
        url_input = st.text_input("Paste Portal URL:")
        if st.button("Scrape Bids"):
            with st.spinner("Searching portal..."):
                st.session_state.all_bids = scrape_stable_bids(url_input)
                st.rerun()
