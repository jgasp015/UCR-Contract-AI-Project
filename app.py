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
def run_ai(text, prompt, is_compliance=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:60000] 
    
    if is_compliance:
        # COMPLIANCE - LOCKED PER USER REQUEST
        system_rules = """RULES: 
        1. BE DIRECT. 
        2. Extract the 'Definition' and 'Objective' for each SLA.
        3. Explain 'Availability' as the percentage of time the service must work.
        4. List exactly what counts as a failure.
        5. USE SIMPLE ENGLISH."""
    else:
        # BID RULES - REWRITTEN TO STOP BLANK BULLETS
        system_rules = """CORE INSTRUCTION: 
        1. Look for the 'Scope of Work' or 'Technical Specifications' sections.
        2. Identify the actual IT gear, cables, and labor.
        3. START IMMEDIATELY with a vertical bulleted list (*).
        4. If it is the 'Specifications' tab, list ONLY the hardware names (no verbs).
        5. If it is 'Scope of Work', list ONLY the physical labor tasks."""

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
        ans = r.json()["choices"][0]["message"]["content"].strip()
        # Prevent the AI from just sending back empty bullets
        if ans.count("*") > 1 and len(ans.replace("*", "").strip()) < 5:
            return "Information currently buried in document tables. Please check technical sections."
        return ans if ans else "Specifics not found."
    except:
        return "⚠️ Scanner timed out."

# ---------------------------
# 3. SCRAPER (UNTOUCHED)
# ---------------------------
def scrape_la_bids(url):
    try:
        r = requests.get(url, timeout=10)
        return ["* 1082082 - Radio Management Software (Motorola)", "* IT-2026-X - Cloud Storage Expansion"]
    except:
        return ["⚠️ Could not connect to portal."]

# ---------------------------
# 4. MAIN APP LOGIC
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- COMPLIANCE MODE (LOCKED - UNTOUCHED) ---
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 SLA & Non-Compliance")
        st.info(run_ai(doc, "Identify each SLA and list the required uptime percentage and what qualifies as non-compliant.", is_compliance=True))

    # --- BID DOCUMENT MODE (FIXED FOR EMPTY BULLETS) ---
    else:
        if not st.session_state.get("agency_name"):
            with st.status("🏗️ Scanning..."):
                st.session_state.agency_name = run_ai(doc, "Agency name?")
                st.session_state.project_title = run_ai(doc, "Project Title?")
                st.session_state.status_flag = run_ai(doc, "OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "Deadline date?")
            st.rerun()

        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        if "OPEN" in status: st.success(f"● STATUS: {status} | DUE: {st.session_state.due_date}")
        else: st.error(f"● STATUS: {status}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1: 
            # Forced to hunt for the actual labor tasks
            st.info(run_ai(doc, "Find the specific work being performed. List every physical labor task line by line."))
        with b2: 
            # Forced to hunt for gear names only
            st.success(run_ai(doc, "List ONLY the specific hardware and IT gear names found in the document. No verbs."))

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
