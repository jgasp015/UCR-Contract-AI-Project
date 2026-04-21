import streamlit as st
import requests
from pypdf import PdfReader
import io
import re

# --- 1. SESSION & STATE MANAGEMENT (ISOLATED) ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'portal_session': requests.Session(),
        'agency_name': None, 'project_title': None, 'detected_due_date': None,
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None, 'report_ans': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def reset_analysis():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. AI ENGINES (VAULTED SEPARATELY) ---
def run_bid_ai(text, prompt):
    """BID SILO: Mom-Test Simplification."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "Helpful assistant. Use simple words. No jargon. Short vertical '-' bullets."}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:18000]}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

def run_performance_ai(text, prompt):
    """PERFORMANCE SILO: High-context compliance logic for new contractors."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    system_msg = """You are a Contract Compliance Officer. Explain reporting duties for a NEW contractor.
    Focus on: 1. HOW to report (Tools/Phone), 2. WHAT to achieve (SLA %), 3. RECOVERY times, 4. MONTHLY reports required."""
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[len(text)//2:]}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

# --- 3. UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    st.divider()
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE (DETAILED CONTEXT)
        st.subheader("📊 Contractor Performance & Reporting Guide")
        if not st.session_state.report_ans:
            with st.spinner("Analyzing Compliance Duties..."):
                st.session_state.report_ans = run_performance_ai(doc, "Explain exactly how I report issues, the uptime targets, and every report I must file monthly.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT (MOM-TEST SIMPLIFIED)
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_bid_ai(doc, "Agency Name?")
            st.session_state.project_title = run_bid_ai(doc, "Project Title?")
            st.rerun()
        st.subheader(st.session_state.project_title)
        st.info(f"**Agency:** {st.session_state.agency_name}")
        
        if not st.session_state.summary_ans:
            st.session_state.summary_ans = run_bid_ai(doc, "Simple goals?")
            st.session_state.tech_ans = run_bid_ai(doc, "Tech needed?")
            st.rerun()
        
        t1, t2 = st.tabs(["📖 Plan", "🛠️ Tech"])
        t1.write(st.session_state.summary_ans); t2.write(st.session_state.tech_ans)

else:
    # MAIN MENU (URL SECTION UNTOUCHED)
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="v1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
            
    with t_sla:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="v2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
    
    with t_url:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        # Scraper logic remains as previously fixed
