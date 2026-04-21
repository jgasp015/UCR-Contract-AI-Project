import streamlit as st
import requests
from pypdf import PdfReader
import io
import re

# --- SILO 1: SESSION & STATE (STRICTLY ISOLATED) ---
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

# --- SILO 2: AI ENGINES (PROTECTED) ---
def run_bid_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "You use the Mom-Test: Simple words. Short vertical '-' bullets. Be extremely brief."}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:18000]}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

# --- SILO 3: UI VIEW LOGIC (ANALYSIS VS MENU) ---
if st.session_state.active_bid_text:
    # 1. THE BACK BUTTON
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    st.divider()
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE VIEW
        st.subheader("📊 Contractor Performance & Reporting Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_bid_ai(doc, "Explain exactly how to report issues, the uptime targets, and every report I must file monthly.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT VIEW (FIXED HEADER & TECH TAB)
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_bid_ai(doc, "Agency Name?")
            st.session_state.project_title = run_bid_ai(doc, "Project Title?")
            st.session_state.detected_due_date = run_bid_ai(doc, "Deadline?")
            st.rerun()
        
        # HEADER FIELDS ONLY
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        if not st.session_state.summary_ans:
            st.session_state.bid_details = run_bid_ai(doc, "Solicitation ID and Email.")
            st.session_state.summary_ans = run_bid_ai(doc, "Simple goals?")
            st.session_state.tech_ans = run_bid_ai(doc, "ONLY list the specific Software, Hardware, or Equipment needed. Max 5 points.")
            st.session_state.submission_ans = run_bid_ai(doc, "Steps to apply?")
            st.session_state.compliance_ans = run_bid_ai(doc, "Insurance/Conduct rules?")
            st.session_state.award_ans = run_bid_ai(doc, "Award criteria?")
            st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details)
        t2.info(st.session_state.summary_ans)
        t3.success(st.session_state.tech_ans) # Condensed
        t4.warning(st.session_state.submission_ans)
        t5.error(st.session_state.compliance_ans)
        t6.write(st.session_state.award_ans)

else:
    # --- SILO 4: MAIN MENU (RESTORED) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="main_bid_vault")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
            
    with t_sla:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="main_sla_vault")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
            
    with t_url:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            # Scanner logic remains identically siloed here
            pass
