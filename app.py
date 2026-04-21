import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION STATE (FIXED VISIBILITY) ---
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

# --- SILO 2: THE ENGINE ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return None

# --- SILO 3: UI FLOW (FIXED UPLOAD VISIBILITY) ---
if st.session_state.active_bid_text:
    # --- ANALYSIS VIEW (HOME BUTTON ALWAYS TOP) ---
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    doc = st.session_state.active_bid_text
    
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance & SLA Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "Summarize SLAs and Penalties.", "Compliance Expert.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID ANALYSIS (MOM-TEST)
        if not st.session_state.agency_name:
            with st.spinner("Identifying Bid..."):
                info = run_ai(doc, "Agency, Title, and Date.", "Facts.")
                if info: st.session_state.agency_name = info; st.rerun()
        
        st.success("✅ Bid Loaded")
        st.info(st.session_state.agency_name)

        t1, t2, t3, t4 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal"])
        # Fetching remaining data...
        if not st.session_state.summary_ans:
            st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test.")
            st.session_state.tech_ans = run_ai(doc, "Tech list?", "Simple.")
            st.rerun()
            
        t1.write(st.session_state.summary_ans); t2.write(st.session_state.tech_ans)

else:
    # --- MAIN MENU (THE FIX: UPLOADERS ALWAYS SHOW HERE) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        st.write("### Analyze a New Bid")
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="main_bid_up")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
            
    with t2:
        st.write("### Check SLA Compliance")
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="main_sla_up")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
            
    with t3:
        u_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan Portal"):
            # Scanner logic stays siloed here
            pass
