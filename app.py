import streamlit as st
import requests
from pypdf import PdfReader
import io

# --- 1. SESSION STATE (RESTORED TO FAST-LOAD) ---
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"
if 'portal_hits' not in st.session_state: st.session_state.portal_hits = []

def reset_analysis():
    for key in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 
                'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[key] = None

# Initialize keys if missing
for key in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 
            'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. FAST-AI ENGINE (RESTORED) ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] if context_slice == "start" else text[:10000] + "\n[...]\n" + text[-10000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ Busy. Try clicking the tab again."

# --- 3. UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE
        st.subheader("📊 Performance & SLA Rules")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "Explain reporting, uptime, penalties, and stop-clock.", "Compliance Officer.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT (FAST LOAD)
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency?", "Name only.", "start")
            st.session_state.project_title = run_ai(doc, "Project?", "Name only.", "start")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
            st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        if not st.session_state.summary_ans:
            st.session_state.bid_details = run_ai(doc, "ID/Email.", "Facts.", "start")
            st.session_state.summary_ans = run_ai(doc, "Goals?", "Mom-test simple points.")
            st.session_state.tech_ans = run_ai(doc, "Specific Software/Hardware? Max 5 points.", "Simple list.")
            st.session_state.submission_ans = run_ai(doc, "Steps to apply?", "1, 2, 3.", "start")
            st.session_state.compliance_ans = run_ai(doc, "Insurance/Behavior rules?", "Simple points.")
            st.session_state.award_ans = run_ai(doc, "How to win?", "Simple list.")
            st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details)
        t2.info(st.session_state.summary_ans)
        t3.success(st.session_state.tech_ans)
        t4.warning(st.session_state.submission_ans)
        t5.error(st.session_state.compliance_ans)
        t6.write(st.session_state.award_ans)

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
    with t3:
        u_in = st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            # Scanner logic stays locked here
            pass
