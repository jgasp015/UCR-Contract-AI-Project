import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE INITIALIZATION ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.session_state.active_bid_text = None
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE CLEAN ENGINE ---
def run_ai(text, prompt, persona="Helper"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Scan start and end for dates
    ctx = text[:12000] + "\n...\n" + text[-5000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"You are a {persona}. RULES: NO INTROS. VERTICAL BULLETS ONLY. IF MISSING, SAY 'HIDEME'."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: return None

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 4. MAIN LOGIC ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # HEADER DATA
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Analyzing..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?")
            st.session_state.status_flag = run_ai(doc, "Status: OPEN or CLOSED?")
        st.rerun()

    # CLEAN HEADER DISPLAY (Only show if data exists)
    if st.session_state.status_flag: st.success(f"● STATUS: {st.session_state.status_flag.upper()}")
    if st.session_state.detected_due_date: st.write(f"**📅 DUE:** {st.session_state.detected_due_date}")
    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 BID:** {st.session_state.project_title}")
    st.divider()

    # --- MODE 1: COMPLIANCE REQUIREMENTS ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin Rules"])
        with t1:
            if not st.session_state.get('rep_what'): st.session_state.rep_what = run_ai(doc, "What data needs reporting?", "Auditor")
            st.info(st.session_state.rep_what if st.session_state.rep_what else "Reporting requirements not found.")
        with t2:
            if not st.session_state.get('rep_viol'): st.session_state.rep_viol = run_ai(doc, "What counts as a violation?", "Auditor")
            st.error(st.session_state.rep_viol if st.session_state.rep_viol else "Violations not found.")
        with t3:
            if not st.session_state.get('rep_rem'): st.session_state.rep_rem = run_ai(doc, "What are the penalties?", "Auditor")
            st.warning(st.session_state.rep_rem if st.session_state.rep_rem else "Remedies not found.")
        with t4:
            if not st.session_state.get('rep_freq'): st.session_state.rep_freq = run_ai(doc, "How often is reporting due?", "Auditor")
            st.success(st.session_state.rep_freq if st.session_state.rep_freq else "Frequency not found.")
        with t5:
            if not st.session_state.get('rep_admin'): st.session_state.rep_admin = run_ai(doc, "Admin submission rules?", "Auditor")
            st.write(st.session_state.rep_admin if st.session_state.rep_admin else "Admin rules not found.")

    # --- MODE 2: BID DOCUMENT ---
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Award"])
        with b1:
            if not st.session_state.get('summary_ans'): st.session_state.summary_ans = run_ai(doc, "3 simple goals.")
            st.info(st.session_state.summary_ans if st.session_state.summary_ans else "Goals not found.")
        with b2:
            if not st.session_state.get('tech_ans'): st.session_state.tech_ans = run_ai(doc, "Required tools?")
            st.success(st.session_state.tech_ans if st.session_state.tech_ans else "Tech not found.")
        with b3:
            if not st.session_state.get('submission_ans'): st.session_state.submission_ans = run_ai(doc, "3 steps to apply.")
            st.warning(st.session_state.submission_ans if st.session_state.submission_ans else "Steps not found.")
        with b4:
            if not st.session_state.get('compliance_ans'): st.session_state.compliance_ans = run_ai(doc, "Insurance/Legal rules?")
            st.error(st.session_state.compliance_ans if st.session_state.compliance_ans else "Rules not found.")
        with b5:
            if not st.session_state.get('award_ans'): st.session_state.award_ans = run_ai(doc, "How to win?")
            st.write(st.session_state.award_ans if st.session_state.award_ans else "Award info not found.")

# --- 5. INITIAL MENU ---
else:
    st.title("🏛️ Reporting Tool")
    tab_bid, tab_comp, tab_url = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="main_bid")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
            
    with tab_comp:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="main_comp")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
            
    with tab_url:
        u_in = st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"):
            st.info("Scanner results will appear here. Please upload the PDF to a tab above for deep analysis.")    
