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
    st.error("🔑 API Key missing in Streamlit Secrets!")
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
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    try:
        # Standard Streamlit Cloud browser initialization
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(15)
        driver.get(url)
        time.sleep(8) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        found_bids = []
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            if len(text) > 35 and not any(x in text.lower() for x in ["login", "register", "support"]):
                clean_name = text.upper()
                bid_link = urljoin(url, link['href'])
                if clean_name[:40] not in [b['name'][:40] for b in found_bids]:
                    found_bids.append({"name": clean_name, "full_text": f"TITLE: {clean_name}", "link": bid_link})
        return found_bids[:8]
    except Exception as e:
        # Return empty list instead of crashing, so the UI stays visible
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Reset App"):
        for key in keys: st.session_state[key] = None
        st.session_state.active_bid_text = None
        st.rerun()

input_mode = st.radio("Choose Input:", ["Portal Link", "Upload PDF", "Manual Paste"])

if st.session_state.active_bid_text is None:
    if input_mode == "Portal Link":
        url_input = st.text_input("Enter Portal URL:")
        if url_input:
            with st.spinner("Searching..."):
                bids = scrape_stable_bids(url_input)
            if bids:
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"**{bid['name']}**")
                        if st.button("Analyze", key=f"b_{idx}"):
                            st.session_state.active_bid_text = bid['full_text']
                            st.rerun()
            else:
                st.error("Site blocked the scraper. Use 'Manual Paste' instead.")

    elif input_mode == "Upload PDF":
        up = st.file_uploader("Upload PDF", type="pdf")
        if up:
            pdf = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in pdf.pages])
            st.rerun()

    else:
        text = st.text_area("Paste text here:")
        if st.button("Analyze Text"):
            st.session_state.active_bid_text = text
            st.rerun()

# --- 4. DISPLAY ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("Analyzing...") as s:
            doc = st.session_state.active_bid_text
            st.session_state.status_flag = deep_query(doc, "Status: OPEN or CLOSED?", max_tokens=5)
            st.session_state.summary_ans = deep_query(doc, "Summarize goal/scope.")
            st.session_state.tech_ans = deep_query(doc, "List IT/Tech requirements.")
            st.session_state.submission_ans = deep_query(doc, "Due dates/steps.")
            st.session_state.compliance_ans = deep_query(doc, "Insurance/Legal.")
            st.session_state.award_ans = deep_query(doc, "Award info.")
            st.session_state.total_saved += 150
            st.rerun()

    st.write(f"### STATUS: {st.session_state.status_flag}")
    t1, t2, t3, t4 = st.tabs(["Overview", "Tech", "Dates", "Legal"])
    t1.write(st.session_state.summary_ans)
    t2.write(st.session_state.tech_ans)
    t3.write(st.session_state.submission_ans)
    t4.write(st.session_state.compliance_ans)
