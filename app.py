import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# 5-Tab Persistence Keys
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Check your Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. HIGH-SPEED FUNCTIONS ---

@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def scrape_multi_it_bids(url):
    it_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev ", "cabling", "fiber", "saas", "cloud"]
    ignore_words = ["page", "showing", "log out", "reset", "next", "contact us"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all(['tr', 'div', 'li'])
        found_bids = []
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            if any(k in text.lower() for k in it_keywords) and not any(i in text.lower() for i in ignore_words):
                if len(text) > 45:
                    link_tag = row.find('a', href=True)
                    bid_link = urljoin(url, link_tag['href']) if link_tag else url
                    if text[:60] not in [b['name'][:60] for b in found_bids]:
                        found_bids.append({"name": text[:120], "full_text": text, "link": bid_link})
        return found_bids[:10]
    except:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.cache_data.clear()
        for key in ['active_bid_text'] + keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

# --- DATA LOADING (LIVE LINK RESTORED) ---
if not st.session_state.active_bid_text:
    if input_mode == "Live Portal Link":
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            with st.spinner("Scanning portal for Technology Bids..."):
                bids = scrape_multi_it_bids(url_input)
                if bids:
                    for idx, bid in enumerate(bids):
                        with st.container(border=True):
                            st.write(f"### 📦 {bid['name']}")
                            st.markdown(f"🔗 [Direct Link]({bid['link']})")
                            if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                                st.session_state.active_bid_text = bid['full_text']
                                st.rerun()
                else:
                    st.warning("No IT bids found on this page.")

    elif input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:6000]
            st.rerun()

# --- 4. INSTANT 5-TAB ANALYSIS ---
if st.session_state.active_bid_text:
    
    if not st.session_state.summary_ans:
        with st.status("⚡ Paid Tier: High-Speed Full Lifecycle Analysis", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast(f"Status (Active/Awarded/Closed): {st.session_state.active_bid_text}", "Auditor")
            st.session_state.summary_ans = query_groq_fast(f"Summarize goal: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.tech_ans = query_groq_fast(f"List ONLY IT hardware/cabling/software: {st.session_state.active_bid_text}", "IT Auditor")
            st.session_state.submission_ans = query_groq_fast(f"Deadlines and submission steps: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.compliance_ans = query_groq_fast(f"Identify mandatory rules and reporting: {st.session_state.active_bid_text}", "Legal Lead")
            st.session_state.award_ans = query_groq_fast(f"Extract Awarded Vendor and Contract Amount: {st.session_state.active_bid_text}", "Financial Auditor")
            
            st.session_state.total_saved += 100 
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    if st.session_state.status_flag and "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    st.divider()
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
