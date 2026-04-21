import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE ---
def init_all_states():
    defaults = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'analysis_mode': "Standard", 'total_saved': 0,
        'agency_name': None, 'project_title': None, 'summary_ans': None,
        'tech_ans': None, 'submission_ans': None, 'compliance_ans': None,
        'award_ans': None, 'report_ans': None, 'status_flag': None, 'detected_due_date': None
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

init_all_states()

# SAFE KEY LOADING
if "GROQ_API_KEY" not in st.secrets:
    st.error("🔑 Key missing in Streamlit Secrets! Please add it to the dashboard settings.")
    st.stop()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE AI ENGINE ---
def deep_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Government Data Extractor. Concise facts. NO INTROS."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:12000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Connection Error"

# --- 3. UI FLOW (RESTORED JEFFREY GASPAR STYLE) ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Return Home"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back to List"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.spinner("Analyzing Document..."):
            st.session_state.agency_name = deep_query(doc, "Agency name?")
            st.session_state.project_title = deep_query(doc, "Project title?")
            st.session_state.detected_due_date = deep_query(doc, "Deadline? (MM/DD/YYYY).")
            st.session_state.status_flag = deep_query(doc, "Status: OPEN, CLOSED, or AWARDED?").upper()
            st.rerun()

    status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"
    if "OPEN" in status: st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    elif "AWARDED" in status: st.info(f"● AWARDED | Project Completed")
    else: st.error(f"● {status} | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    
    tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    if not st.session_state.summary_ans:
        with st.status("🚀 Deep Scanning..."):
            st.session_state.summary_ans = deep_query(doc, "Project goal.")
            st.session_state.tech_ans = deep_query(doc, "Required gear.")
            st.session_state.submission_ans = deep_query(doc, "Steps to apply.")
            st.session_state.compliance_ans = deep_query(doc, "Insurance rules.")
            st.session_state.award_ans = deep_query(doc, "Winner selection.")
            st.session_state.total_saved += 120
            st.rerun()
    
    tabs[0].info(st.session_state.summary_ans)
    tabs[1].success(st.session_state.tech_ans)
    tabs[2].warning(st.session_state.submission_ans)
    tabs[3].error(st.session_state.compliance_ans)
    tabs[4].write(st.session_state.award_ans)

else:
    t1, t2, t3 = st.tabs(["📄 Upload Bid", "📊 Contract Performance", "🔗 Scan Portal"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with t3:
        url = st.text_input("Portal URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan"):
            st.info("Scanner logic active. Please upload result PDF to analyze.")
