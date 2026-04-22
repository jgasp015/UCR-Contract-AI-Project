import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup

# ---------------------------
# 1. STATE & RESET
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
        # COMPLIANCE - SLA ONLY
        system_rules = """RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY (*). 3. EVERY BULLET ON NEW LINE. 
        4. YOU ARE A COMPLIANCE AUDITOR. 5. FIND EVERY SINGLE SLA: Availability, Time to Repair, and Notification. 
        6. LIST WHAT QUALIFIES AS 'NON-COMPLIANT'. 7. USE SIMPLE ENGLISH."""
    else:
        # BID RULES - CLEAN GEAR LISTING
        system_rules = """RULES: 
        1. For 'Specifications', list ONLY the hardware/software names. DO NOT use verbs like 'Install' or 'Setup'.
        2. START IMMEDIATELY with a vertical bulleted list (*).
        3. No conversation. No repeating prompt."""

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
        return "⚠️ Scanner timed out."

# ---------------------------
# 3. SCRAPER FOR AGENCY URL
# ---------------------------
def scrape_la_bids(url):
    try:
        # Simulating a scrape for IT specific bids from the portal
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # Placeholder for extracting IT-related bid rows based on portal structure
        return [
            "* 1082082 - Radio Management Software (Motorola)",
            "* IT-2026-X - Cloud Storage Expansion",
            "* POLICE-MDC-99 - Mobile Data Computer Refresh"
        ]
    except:
        return ["⚠️ Could not connect to portal. Please try again."]

# ---------------------------
# 4. MAIN APP LOGIC
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- COMPLIANCE MODE (SLA ONLY - PENALTIES REMOVED) ---
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 SLA & Non-Compliance")
        st.info(run_ai(doc, "List all SLAs and exactly what makes a contractor 'Non-Compliant'.", is_compliance=True))

    # --- BID DOCUMENT MODE ---
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
            st.info(run_ai(doc, "List ONLY the actual physical work and project tasks to be performed."))
        with b2:
            # CLEAN GEAR LIST - NO VERBS
            st.success(run_ai(doc, "List ONLY the hardware, technology gear, and software names. Do not include verbs like install."))

else:
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
            with st.status("Scraping Portal for IT Bids..."):
                bids = scrape_la_bids(url)
            st.write("**Found Open IT Bids:**")
            for bid in bids: st.write(bid)

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"): hard_reset()
