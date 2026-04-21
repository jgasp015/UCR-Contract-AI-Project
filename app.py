import streamlit as st
import requests
from pypdf import PdfReader
import io
import time

# --- SILO 1: SESSION & STATE (WITH PERSISTENCE) ---
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

# --- SILO 2: THE "PERSISTENT" AI ENGINE ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    # If we already have the answer in memory, don't ask the AI again
    # This prevents hitting the rate limit twice for the same data
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] if context_slice == "start" else text[:10000] + "\n[...]\n" + text[-10000:]
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    
    try:
        # Extra pause to cool down the API
        time.sleep(1.2) 
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return None # Return None so the app knows to try again later
    except:
        return None

# --- SILO 3: UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance & SLA Rules")
        if not st.session_state.report_ans:
            with st.spinner("Analyzing..."):
                res = run_ai(doc, "Explain reporting, uptime, penalties, and stop-clock.", "Compliance Officer.")
                if res: st.session_state.report_ans = res; st.rerun()
        st.markdown(st.session_state.report_ans if st.session_state.report_ans else "⚠️ AI busy. Please wait 5 seconds and refresh.")
    
    else:
        # STAGGERED LOADING: Header First
        if not all([st.session_state.agency_name, st.session_state.project_title]):
            with st.status("Fetching Header...") as s:
                if not st.session_state.agency_name: st.session_state.agency_name = run_ai(doc, "Agency?", "Name only.", "start")
                if not st.session_state.project_title: st.session_state.project_title = run_ai(doc, "Project?", "Name only.", "start")
                if not st.session_state.detected_due_date: st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
                st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        # TAB LOADING: One by one
        if not st.session_state.summary_ans:
            with st.status("Analyzing Tabs...") as s:
                if not st.session_state.bid_details: st.session_state.bid_details = run_ai(doc, "ID/Email.", "Facts.", "start")
                if not st.session_state.summary_ans: st.session_state.summary_ans = run_ai(doc, "Goals?", "Simple.")
                if not st.session_state.tech_ans: st.session_state.tech_ans = run_ai(doc, "Tech?", "Simple.")
                st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].markdown(st.session_state.bid_details if st.session_state.bid_details else "Loading...")
        tabs[1].info(st.session_state.summary_ans if st.session_state.summary_ans else "Loading...")
        tabs[2].success(st.session_state.tech_ans if st.session_state.tech_ans else "Loading...")
        
        # Trigger next batch if needed
        if not st.session_state.submission_ans:
             st.session_state.submission_ans = run_ai(doc, "Steps?", "1,2,3.", "start")
             st.session_state.compliance_ans = run_ai(doc, "Rules?", "Simple.")
             st.session_state.award_ans = run_ai(doc, "Winner?", "Simple.")
             st.rerun()

        tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans)
        tabs[5].write(st.session_state.award_ans)

else:
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
