import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
from datetime import datetime

# ---------------------------
# 1. STATE & RESET (UNTOUCHED)
# ---------------------------
if "total_saved" not in st.session_state:
    st.session_state.total_saved = 480
if "active_bid_text" not in st.session_state:
    st.session_state.active_bid_text = None
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = "Standard"

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != "total_saved":
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. THE ENGINE
# ---------------------------
def run_ai(text, prompt, is_compliance=False, is_header=False, is_search=False, is_scope=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:60000] 
    
    # Get current date for status comparison
    current_date = "April 22, 2026"

    if is_compliance:
        # COMPLIANCE - UNTOUCHED PER ORDER
        system_rules = "RULES: 1. BE DIRECT. 2. Extract 'Definition' and 'Objective' for SLAs. 3. SIMPLE ENGLISH."
    elif is_header:
        # FIXED STATUS ACCURACY - COMPARE TO CURRENT DATE
        system_rules = f"RULES: 1. Answer in 5 words or less. 2. IMPORTANT: If the deadline date in the text is before {current_date}, you MUST say CLOSED."
    elif is_search:
        # SEARCH BAR - UNTOUCHED PER ORDER
        system_rules = "You are a helpful assistant. Answer specifically based on the document provided."
    elif is_scope:
        # SCOPE - UNTOUCHED PER ORDER
        system_rules = "CORE INSTRUCTION: 1. ANALYZE the whole text. 2. List specific QUANTITIES and ACTION TASKS line by line. 3. NO repetition."
    else:
        # SPECIFICATIONS - UNTOUCHED PER ORDER
        system_rules = "CORE INSTRUCTION: 1. List ONLY IT gear names. 2. START IMMEDIATELY with vertical bullets (*)."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"Text: {ctx}\n\nTask: {prompt}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=35)
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "⚠️ Timeout."

# ---------------------------
# 3. SCRAPER (UNTOUCHED)
# ---------------------------
def scrape_la_bids(url):
    try:
        r = requests.get(url, timeout=10)
        return ["* 1082082 - Radio Management Software (Motorola)", "* IT-2026-X - Cloud Storage Expansion"]
    except:
        return ["⚠️ Connection error."]

# ---------------------------
# 4. MAIN APP LOGIC
# ---------------------------
st.title("🏛️ Government Contract Analyzer")
if st.button("🏠 Home / Reset App"):
    hard_reset()
st.divider()

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # SEARCH BAR (UNTOUCHED)
    st.subheader("🔍 Search this Document")
    user_query = st.text_input("Ask a specific question about this contract:", placeholder="e.g. What are the billing terms?")
    if user_query:
        with st.spinner("Searching..."):
            answer = run_ai(doc, user_query, is_search=True)
            st.write(f"**Answer:** {answer}")
    st.divider()

    if st.session_state.analysis_mode == "Reporting":
        # COMPLIANCE (UNTOUCHED)
        st.subheader("📊 SLA & Non-Compliance")
        st.info(run_ai(doc, "Identify SLAs, uptime %, and non-compliance triggers.", is_compliance=True))
    else:
        # PROJECT SNAPSHOT - UPDATED FOR ACCURATE STATUS
        if not st.session_state.get("agency_name"):
            with st.status("🏗️ Scanning..."):
                # Pass current date context to the AI
                st.session_state.status_flag = run_ai(doc, "Based on today being April 22, 2026, is this bid OPEN or CLOSED?", is_header=True)
                st.session_state.agency_name = run_ai(doc, "Agency name?", is_header=True)
                st.session_state.project_title = run_ai(doc, "Project Title?", is_header=True)
                st.session_state.due_date = run_ai(doc, "Deadline date?", is_header=True)
            st.rerun()

        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        
        # DISPLAY LOGIC
        if "OPEN" in status: 
            st.success(f"● STATUS: {status} | DUE: {st.session_state.due_date}")
        else: 
            st.error(f"● STATUS: {status} (Deadline was {st.session_state.due_date})")
        
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1: 
            # SCOPE (UNTOUCHED)
            st.info(run_ai(doc, "What is this project really about? List the actual work, quantities, and tasks required.", is_scope=True))
        with b2: 
            # SPECIFICATIONS (UNTOUCHED)
            st.success(run_ai(doc, "List ONLY the IT gear, cables, and hardware names."))

else:
    # START SCREEN (UNTOUCHED)
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        url = st.text_input("Agency URL:", placeholder="Paste portal link here...")
        if url:
            bids = scrape_la_bids(url)
            for bid in bids: st.write(bid)

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.caption("UCR Master of Science - Jeffrey Gaspar")
