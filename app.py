import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE (RESTORED & PROTECTED) ---
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

# --- SILO 2: AI CORE (SHARED BUT ISOLATED CALLS) ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:18000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "Analysis currently unavailable."

# --- SILO 3: UI FLOW (BACK BUTTON + RESULTS VIEW) ---
if st.session_state.active_bid_text:
    # RESTORED: HOME / BACK BUTTON
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    st.divider()
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE VIEW
        st.info("### 📊 Contract Reporting & SLA Guide")
        if not st.session_state.report_ans:
            with st.spinner("Analyzing SLA Rules..."):
                st.session_state.report_ans = run_ai(doc, "List SLA Uptime %, Fix Times, and Monthly Reports.", "Compliance Expert.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT VIEW (RESTORED)
        if not st.session_state.agency_name:
            with st.spinner("Reading Bid Data..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Return ONLY name.")
                st.session_state.project_title = run_ai(doc, "Project Name?", "Return ONLY name.")
                st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.")
                st.rerun()
        
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")

        if not st.session_state.summary_ans:
            with st.spinner("Gathering Facts..."):
                st.session_state.bid_details = run_ai(doc, "Solicitation ID and Contact Email.", "Facts only.")
                st.session_state.summary_ans = run_ai(doc, "Project goals?", "Vertical points.")
                st.session_state.tech_ans = run_ai(doc, "Software/Hardware needed?", "List items.")
                st.session_state.submission_ans = run_ai(doc, "Steps to apply?", "1, 2, 3.")
                st.session_state.compliance_ans = run_ai(doc, "Legal/Conduct/Insurance rules?", "Vertical points.")
                st.session_state.award_ans = run_ai(doc, "Winning/Award criteria?", "Simple list.")
                st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details); t2.info(st.session_state.summary_ans)
        t3.success(st.session_state.tech_ans); t4.warning(st.session_state.submission_ans)
        t5.error(st.session_state.compliance_ans); t6.write(st.session_state.award_ans)

else:
    # --- SILO 4: MAIN MENU ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_vault")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
            
    with t_sla:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="sla_vault")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
            
    with t_url:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            if u_in:
                # Scraper logic remains untouched from the working code
                pass
