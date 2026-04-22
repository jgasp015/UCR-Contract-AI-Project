import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 

def hard_reset():
    keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 
            'rep_what', 'rep_viol', 'rep_rem', 'rep_freq', 'rep_admin', 'status_flag', 
            'agency_name', 'project_title', 'detected_due_date']
    for k in keys: st.session_state[k] = None
    st.session_state.active_bid_text = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. ENGINE ---
def run_ai(text, prompt, persona="Simple Assistant"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Clean the text to prevent "CALNET" loops
    clean_text = text.replace("Contract Manager", "").replace("CALNET", "")[:15000]
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"You are a {persona}. RULES: 1. BE EXTREMELY BRIEF. 2. USE BULLETS. 3. NO JARGON. 4. IF DATA IS MISSING, SAY 'NOT FOUND'."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{clean_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Busy. Try again."

# --- 3. UI ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset"):
        hard_reset(); st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # 4-ITEM HEADER (ONLY)
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Analyzing..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?", "Data Finder")
            st.session_state.project_title = run_ai(doc, "Project Title?", "Data Finder")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Data Finder")
            st.session_state.status_flag = run_ai(doc, "Status: OPEN or CLOSED?", "Data Finder").upper()
        st.rerun()

    st.success(f"● STATUS: {st.session_state.status_flag}")
    st.write(f"**📅 DUE:** {st.session_state.detected_due_date} | **🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID:** {st.session_state.project_title}")
    st.divider()

    if st.session_state.analysis_mode == "Reporting":
        # --- COMPLIANCE TABS (NEW) ---
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin Rules"])
        with t1:
            if not st.session_state.get('rep_what'): st.session_state.rep_what = run_ai(doc, "What specific data needs reporting? (Sales, Uptime, etc.)", "Compliance Expert")
            st.info(st.session_state.rep_what)
        with t2:
            if not st.session_state.get('rep_viol'): st.session_state.rep_viol = run_ai(doc, "What counts as a violation or SLA breach?", "Compliance Expert")
            st.error(st.session_state.rep_viol)
        with t3:
            if not st.session_state.get('rep_rem'): st.session_state.rep_rem = run_ai(doc, "What are the penalties or remedies for failing?", "Compliance Expert")
            st.warning(st.session_state.rep_rem)
        with t4:
            if not st.session_state.get('rep_freq'): st.session_state.rep_freq = run_ai(doc, "How often are reports due? (Monthly, etc.)", "Compliance Expert")
            st.success(st.session_state.rep_freq)
        with t5:
            if not st.session_state.get('rep_admin'): st.session_state.rep_admin = run_ai(doc, "What are the admin rules or portal submission steps?", "Compliance Expert")
            st.write(st.session_state.rep_admin)
    else:
        # --- BID TABS (SIMPLIFIED) ---
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Award"])
        with b1:
            if not st.session_state.get('summary_ans'): st.session_state.summary_ans = run_ai(doc, "3 simple project goals.")
            st.info(st.session_state.summary_ans)
        with b2:
            if not st.session_state.get('tech_ans'): st.session_state.tech_ans = run_ai(doc, "List required tools/software.")
            st.success(st.session_state.tech_ans)
        with b3:
            if not st.session_state.get('submission_ans'): st.session_state.submission_ans = run_ai(doc, "3 steps to apply.")
            st.warning(st.session_state.submission_ans)
        with b4:
            if not st.session_state.get('compliance_ans'): st.session_state.compliance_ans = run_ai(doc, "Big rules/Insurance.")
            st.error(st.session_state.compliance_ans)
        with b5:
            if not st.session_state.get('award_ans'): st.session_state.award_ans = run_ai(doc, "How to win?")
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
        u_in = st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"):
            st.warning("Scanner active. Upload PDF for deep analysis.")
