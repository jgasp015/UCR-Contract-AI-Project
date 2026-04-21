import streamlit as st
import requests
from pypdf import PdfReader
import io

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

# --- SILO 2: AI ENGINES (CALIBRATED FOR DEPTH) ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Context Slicing: Ensures the AI looks at the right parts of the doc
    if context_slice == "start": ctx = text[:15000]
    elif context_slice == "end": ctx = text[-18000:]
    else: ctx = text[:10000] + "\n[...]\n" + text[-10000:]

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "Analysis failed. Please try again."

# --- SILO 3: UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # 📊 CONTRACT PERFORMANCE: SLA, PENALTY, STOP-CLOCK
        st.subheader("📊 Performance, Penalties & Stop-Clock Rules")
        if not st.session_state.report_ans:
            with st.spinner("Scanning for Penalties & SLA..."):
                prompt = """Explain: 1. HOW to report (Phone/Tool), 2. Uptime targets (%), 3. PENALTIES/Refunds for failure, 4. STOP-CLOCK conditions (when the timer stops), 5. Monthly reports required."""
                st.session_state.report_ans = run_ai(doc, prompt, "SLA Compliance Officer. Be very detailed.", context_slice="full")
        st.markdown(st.session_state.report_ans)
    else:
        # 📄 BID DOCUMENT: SIMPLIFIED ANALYSIS
        if not st.session_state.agency_name:
            with st.status("Reading..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Return ONLY the name.", "start")
                st.session_state.project_title = run_ai(doc, "Project Name?", "Return ONLY the name.", "start")
                st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
                st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        if not st.session_state.summary_ans:
            with st.status("Analyzing Bid..."):
                st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
                st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test points.", "full")
                st.session_state.tech_ans = run_ai(doc, "Software/Hardware needed?", "List items.", "full")
                st.session_state.submission_ans = run_ai(doc, "Steps to apply?", "1, 2, 3.", "start")
                st.session_state.compliance_ans = run_ai(doc, "Rules/Insurance?", "Mom-test points.", "full")
                st.session_state.award_ans = run_ai(doc, "How to win?", "Simple list.", "full")
                st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details); t2.info(st.session_state.summary_ans)
        t3.success(st.session_state.tech_ans); t4.warning(st.session_state.submission_ans)
        t5.error(st.session_state.compliance_ans); t6.write(st.session_state.award_ans)

else:
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    with t_sla:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
    with t_url:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        # (Scraper logic remains identically siloed)
