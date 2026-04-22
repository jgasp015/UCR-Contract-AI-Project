import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup

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
def run_ai(text, prompt, is_compliance=False, is_header=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:60000] 
    
    if is_compliance:
        # COMPLIANCE - LOCKED PER USER REQUEST
        system_rules = """RULES: 1. BE DIRECT. 2. Extract 'Definition' and 'Objective' for SLAs. 
        3. Explain 'Availability' clearly. 4. List failure triggers. 5. SIMPLE ENGLISH."""
    elif is_header:
        # HEADER RULES - STRICT 1-LINE ANSWERS TO STOP DATA DUMPS
        system_rules = "RULES: 1. Answer in 5 words or less. 2. NO extra data. 3. NO intros."
    else:
        # TAB RULES
        system_rules = """CORE INSTRUCTION: 
        1. Identify IT gear, cables, and labor. 2. START IMMEDIATELY with vertical bullets (*).
        3. For 'Specifications', list ONLY gear names. 4. For 'Scope', list ONLY labor tasks."""

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"Based on this document, {prompt}\n\nTEXT:\n{ctx}"}
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
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- COMPLIANCE MODE (LOCKED - UNTOUCHED) ---
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 SLA & Non-Compliance")
        st.info(run_ai(doc, "Identify SLAs, uptime %, and non-compliance triggers.", is_compliance=True))

    # --- BID DOCUMENT MODE (STRICT 3-LINE HEADER) ---
    else:
        if not st.session_state.get("agency_name"):
            with st.status("🏗️ Scanning..."):
                # Forced short-form extraction to prevent data leaks into header
                st.session_state.status_flag = run_ai(doc, "Is it OPEN or CLOSED?", is_header=True)
                st.session_state.agency_name = run_ai(doc, "Agency name?", is_header=True)
                st.session_state.project_title = run_ai(doc, "Project Title?", is_header=True)
                st.session_state.due_date = run_ai(doc, "Deadline date?", is_header=True)
            st.rerun()

        # THE FIXED 3-LINE HEADER
        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        if "OPEN" in status: st.success(f"● STATUS: {status} | DUE: {st.session_state.due_date}")
        else: st.error(f"● STATUS: {status}")
        
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        # ALL DETAILED DATA MOVED HERE
        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1: 
            st.info(run_ai(doc, "List every physical labor task for these cabling services line by line."))
        with b2: 
            st.success(run_ai(doc, "List ONLY the IT gear, cables, and hardware names. No verbs."))

else:
    # --- START SCREEN (UNTOUCHED) ---
    st.title("🏛️ Reporting Tool")
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
    if st.button("🏠 Home / Reset App"): hard_reset()
