import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE INITIALIZATION (RESTORED) ---
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

# --- SECURITY HANDSHAKE (MANDATORY) ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing in Streamlit Secrets!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Government Data Extractor. TODAY'S DATE: April 20, 2026.
                STRICT RULES: 1. NO EXPLANATIONS. 2. NO WORDINESS. 3. CONCISE.
                4. STATUS: Use only 'OPEN', 'CLOSED', or 'AWARDED'."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:15000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Unknown"

def scrape_stable_bids(url):
    """Replaced Selenium with Requests for Cloud Compatibility."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        found_bids = []
        for row in soup.find_all('tr'):
            text = row.get_text(separator=' ', strip=True)
            if any(marker in text.lower() for marker in ["rfb-is-", "rfp-", "solicitation"]):
                clean_name = " ".join(text.split())[:150].upper()
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

    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS VIEW ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to List"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.spinner("Processing Document..."):
            st.session_state.agency_name = deep_query(doc, "Agency name? ONLY the name.")
            st.session_state.project_title = deep_query(doc, "Project title? ONLY the name.")
            st.session_state.detected_due_date = deep_query(doc, "Deadline? (MM/DD/YYYY).")
            status_check = deep_query(doc, "Status: OPEN, CLOSED, or AWARDED? 1 word.")
            st.session_state.status_flag = status_check.upper() if status_check else "UNKNOWN"
            st.rerun()

    # --- SAFETY CHECK: PROTECTS AGAINST CRASH ---
    curr_status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"

    if "OPEN" in curr_status:
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    elif "AWARDED" in curr_status:
        st.info(f"● AWARDED | Project Completed")
    else:
        st.error(f"● {curr_status} | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider()

    # --- TABS SECTION ---
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Analyzing Standards..."):
                st.session_state.report_ans = deep_query(doc, "Factual summary of: 1. Uptime % 2. Fix times 3. Installation rules 4. Penalty credits. NO INTROS.")
                st.session_state.total_saved += 60
                st.rerun()
        st.markdown(st.session_state.report_ans)

    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Performing Deep Scan..."):
                st.session_state.summary_ans = deep_query(doc, "Project goal/purpose. NO INTROS.")
                st.session_state.tech_ans = deep_query(doc, "List required gear/software. NO INTROS.")
                st.session_state.submission_ans = deep_query(doc, "Application steps. NO INTROS.")
                st.session_state.compliance_ans = deep_query(doc, "Insurance/legal rules. NO INTROS.")
                st.session_state.award_ans = deep_query(doc, "Selection process and budget info. NO INTROS.")
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
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze Document", key=f"bid_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.active_bid_name = bid['name']
                st.session_state.analysis_mode = "Standard"
                st.rerun()

# --- VIEW 3: INITIAL SEARCH ---
else:
    t1, t2, t3 = st.tabs(["📄 New Project Search", "📊 Performance Standards", "🔗 Search Online"])
    with t1:
        up_bid = st.file_uploader("Upload Bid PDF", type="pdf", key="up_bid")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.session_state.analysis_mode = "Standard"
            st.rerun()
    with t2:
        up_rep = st.file_uploader("Upload Contract PDF", type="pdf", key="up_rep")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.active_bid_name = up_rep.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with t3:
        url = st.text_input("Paste Portal Link:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan for Opportunities"):
            st.session_state.all_bids = scrape_stable_bids(url)
            st.rerun()
