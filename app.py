import streamlit as st
import requests
import time
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# --- SELENIUM IMPORTS ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

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
            {"role": "system", "content": "You are a concise procurement expert. Provide direct answers without conversational filler."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    if max_tokens: payload["max_tokens"] = max_tokens
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content']
    except:
        return "Analysis timeout or error."

def scrape_stable_bids(url):
    """Uses Selenium to bypass JS rendering issues on BidNet."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the driver
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        
        # Wait for the table to actually load (crucial for BidNet)
        time.sleep(7) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        found_bids = []
        # BidNet usually uses 'solicitation-list-item' or specific anchor classes
        # We look for the descriptive links seen in your screenshot
        for link in soup.find_all('a', href=True):
            text = link.get_text(separator=' ', strip=True)
            
            # Filtering for relevant bids based on length and common keywords
            if len(text) > 30 and not any(x in text.lower() for x in ["login", "register", "support"]):
                clean_name = " ".join(text.split()).upper()
                bid_link = urljoin(url, link['href'])
                
                if clean_name[:50] not in [b['name'][:50] for b in found_bids]:
                    found_bids.append({
                        "name": clean_name, 
                        "full_text": f"PROJECT TITLE: {clean_name}. Found at {url}", 
                        "link": bid_link
                    })
        
        return found_bids[:8]
    except Exception as e:
        st.error(f"Scraper Error: {e}")
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
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link", "Paste Text (Manual)"])

if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.uploader_key}")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            full_content = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.active_bid_text = full_content[:45000] 
            st.rerun()
            
    elif input_mode == "Live Portal Link":
        url_input = st.text_input("Paste Portal URL:", placeholder="https://www.bidnetdirect.com/...")
        if url_input:
            with st.spinner("🕵️ Rendering page and extracting bids..."):
                bids = scrape_stable_bids(url_input)
            
            if bids:
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                            st.session_state.active_bid_text = bid['full_text']
                            st.rerun()
            else:
                st.warning("No bids found. The site might be blocking the automated request or requires a login.")

    else:
        raw_text = st.text_area("Paste the Bid details or Table text here:")
        if st.button("Analyze Pasted Text"):
            st.session_state.active_bid_text = raw_text
            st.rerun()

# --- 4. ANALYSIS & DISPLAY ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🚀 Chained Deep-Scan in Progress...", expanded=True) as status:
            doc = st.session_state.active_bid_text
            
            st.session_state.status_flag = deep_query(doc, "Identify if this bid is OPEN, ACTIVE, CLOSED, or AWARDED. Answer with ONLY the word.", max_tokens=10)
            st.session_state.summary_ans = deep_query(doc, "Summarize the project goal and scope.")
            st.session_state.tech_ans = deep_query(doc, "List all IT requirements, hardware, or technical consulting services mentioned.")
            st.session_state.submission_ans = deep_query(doc, "Identify bid due dates and submission steps.")
            st.session_state.compliance_ans = deep_query(doc, "Identify mandatory insurance and legal rules.")
            st.session_state.award_ans = deep_query(doc, "Identify awarded vendor or total commodity lines.")
            
            st.session_state.total_saved += 150 
            status.update(label="Full Audit Complete!", state="complete", expanded=False)
            st.rerun()

    clean_status = str(st.session_state.status_flag).strip().upper().replace(".", "")
    if any(word in clean_status for word in ["OPEN", "ACTIVE"]):
        st.success(f"✅ STATUS: {clean_status}")
    elif "AWARDED" in clean_status:
        st.info(f"💰 STATUS: {clean_status}")
    else:
        st.error(f"🚨 STATUS: {clean_status}")

    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
