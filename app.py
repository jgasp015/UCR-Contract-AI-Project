import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'portal_session': requests.Session(),
        'agency_name': None, 'project_title': None, 'detected_due_date': None,
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None, 'report_ans': None,
        'total_saved': 0
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def hard_reset():
    # This clears everything to go back to the very beginning
    for key in st.session_state.keys():
        if key != 'total_saved': # Keep the time saved counter
            del st.session_state[key]
    init_state()
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: AI ENGINE ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] if context_slice == "start" else text[:10000] + "\n[...]\n" + text[-10000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": f"{system_msg} Simplify. Mom-test."}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

# --- SILO 3: UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    
    # HOME BUTTON: Now always available when a document is open
    if st.session_state.active_bid_text:
        if st.button("🏠 Home / Back"):
            hard_reset()
            
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # Analysis View
    if not st.session_state.agency_name:
        with st.status("🏗️ Building Header..."):
            st.session_state.agency_name = run_ai(doc, "Agency?", "Name only.", "start")
            st.session_state.project_title = run_ai(doc, "Project Title?", "Name only.", "start")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
        st.rerun()

    st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    
    if not st.session_state.summary_ans:
        with st.status("🚀 Deep Scanning..."):
            st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
            st.session_state.summary_ans = run_ai(doc, "3 simple goals?", "Mom-test.")
            st.session_state.tech_ans = run_ai(doc, "5 tools needed?", "Simple list.")
            st.session_state.submission_ans = run_ai(doc, "3 steps to apply?", "Guide.")
            st.session_state.compliance_ans = run_ai(doc, "Rules/Insurance?", "Simple.")
            st.session_state.award_ans = run_ai(doc, "How to win?", "Simple.")
            st.session_state.total_saved += 120
        st.rerun()

    tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    tabs[0].markdown(st.session_state.bid_details)
    tabs[1].info(st.session_state.summary_ans)
    tabs[2].success(st.session_state.tech_ans)
    tabs[3].warning(st.session_state.submission_ans)
    tabs[4].error(st.session_state.compliance_ans)
    tabs[5].write(st.session_state.award_ans)

else:
    # MAIN MENU
    st.title("🏛️ Reporting Tool")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with t3:
        # THE FIX: Empty URL box
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            # Scanner logic
            pass
