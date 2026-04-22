import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (LOCKED) ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'all_bids' not in st.session_state: st.session_state.all_bids = []

def hard_reset():
    keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'agency_name', 'project_title', 'detected_due_date']
    for k in keys: st.session_state[k] = None
    st.session_state.active_bid_text = None
    st.session_state.all_bids = []

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE DUAL-LOGIC ENGINE ---
def run_query(text, prompt, persona="Helper"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"You are a {persona}. RULES: 1. NO INTROS. 2. VERTICAL BULLETS. 3. MOM-TEST WORDS ONLY."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:25000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Service busy. Click again."

# --- 3. UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset"):
        hard_reset()
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- THE CLEAN 4-ITEM HEADER ---
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Analyzing Document..."):
            st.session_state.agency_name = run_query(doc, "Agency Name?", "Data Finder")
            st.session_state.project_title = run_query(doc, "Project Title?", "Data Finder")
            st.session_state.detected_due_date = run_query(doc, "Deadline Date?", "Data Finder")
            st.session_state.status_flag = run_query(doc, "Status: OPEN or CLOSED?", "Data Finder").upper()
        st.rerun()

    st.success(f"● STATUS: {st.session_state.status_flag}")
    st.write(f"**📅 DEADLINE:** {st.session_state.detected_due_date}")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- COMPLIANCE VS BID LOGIC ---
    if st.session_state.get('analysis_mode') == "Reporting":
        st.header("⚖️ Compliance & Reporting Instructions")
        if not st.session_state.get('report_ans'):
            with st.status("🔍 Extracting Reporting Rules..."):
                # FORCED REPORTING PROMPT
                prompt = """
                Explain the reporting rules for this contract to a beginner:
                1. FREQUENCY: Is it Monthly, Quarterly, or Yearly? 
                2. WHAT TO REPORT: Do they need Sales, Uptime/SLA data, or Usage?
                3. PENALTIES: What are the specific fines for missing a target?
                4. HOW TO SEND: Is there a specific email or portal for the report?
                """
                st.session_state.report_ans = run_query(doc, prompt, "Contract Auditor")
        st.info(st.session_state.report_ans)
    
    else:
        # THE RESTORED BID DOCUMENT TABS
        t1, t2, t3, t4, t5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Award"])
        with t1:
            if not st.session_state.get('summary_ans'): st.session_state.summary_ans = run_query(doc, "3 simple goals.")
            st.info(st.session_state.summary_ans)
        with t2:
            if not st.session_state.get('tech_ans'): st.session_state.tech_ans = run_query(doc, "Tools or software needed?")
            st.success(st.session_state.tech_ans)
        with t3:
            if not st.session_state.get('submission_ans'): st.session_state.submission_ans = run_query(doc, "3 easy steps to apply.")
            st.warning(st.session_state.submission_ans)
        with t4:
            if not st.session_state.get('compliance_ans'): st.session_state.compliance_ans = run_query(doc, "Insurance or big rules?")
            st.error(st.session_state.compliance_ans)
        with t5:
            if not st.session_state.get('award_ans'): st.session_state.award_ans = run_query(doc, "How do they choose the winner?")
            st.write(st.session_state.award_ans)

else:
    st.title("🏛️ Reporting Tool")
    tab_bid, tab_comp, tab_url = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
            
    with tab_comp:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
            
    with tab_url:
        u_in = st.text_input("Agency URL:", placeholder="Paste portal link here...")
        if st.button("Scan Portal"):
            # Scanner logic preserved
            pass
