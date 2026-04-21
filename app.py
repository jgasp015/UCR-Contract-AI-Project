import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (JEFFREY GASPAR STYLE) ---
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

# --- THE KEY HANDSHAKE ---
if "GROQ_API_KEY" not in st.secrets:
    st.error("🔑 KEY MISSING: Go to Streamlit Settings > Secrets and add GROQ_API_KEY")
    st.stop()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE AI ENGINE ---
def deep_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Government Data Extractor. Concise, simple points. NO INTROS."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:12000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        # Small delay to keep the connection stable
        time.sleep(0.5)
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        data = response.json()
        if "choices" in data:
            return data['choices'][0]['message']['content'].strip()
        return "⚠️ AI Busy - Click again"
    except: return "⚠️ Connection error"

# --- 3. UI LOGIC ---
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

    # STEP 1: INITIAL EXTRACTION
    if not st.session_state.agency_name:
        with st.spinner("Processing Document..."):
            st.session_state.agency_name = deep_query(doc, "What is the Government Agency Name?")
            st.session_state.project_title = deep_query(doc, "What is the Project Title?")
            st.session_state.detected_due_date = deep_query(doc, "What is the Deadline? (MM/DD/YYYY)")
            st.session_state.status_flag = deep_query(doc, "Status: OPEN, CLOSED, or AWARDED?").upper()
            st.rerun()

    status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"
    if "OPEN" in status: st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    elif "AWARDED" in status: st.info(f"● AWARDED | Project Completed")
    else: st.error(f"● {status} | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    
    # STEP 2: TABS
    tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal"])
    if not st.session_state.summary_ans:
        with st.status("🚀 Deep Scanning..."):
            st.session_state.summary_ans = deep_query(doc, "Project goal.")
            st.session_state.tech_ans = deep_query(doc, "Tools/Gear needed.")
            st.session_state.submission_ans = deep_query(doc, "How to apply.")
            st.session_state.compliance_ans = deep_query(doc, "Legal/Insurance.")
            st.session_state.total_saved += 120
            st.rerun()
    
    tabs[0].info(st.session_state.summary_ans)
    tabs[1].success(st.session_state.tech_ans)
    tabs[2].warning(st.session_state.submission_ans)
    tabs[3].error(st.session_state.compliance_ans)

else:
    # MAIN MENU
    t1, t2 = st.tabs(["📄 Upload Bid", "🔗 Scan Portal"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.rerun()
    with t2:
        url = st.text_input("Portal Link:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        st.write("Scanner active. Please upload result PDF to analyze.")
