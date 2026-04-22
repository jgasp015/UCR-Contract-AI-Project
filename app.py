import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. SESSION STATE (PRESERVING TIME SAVED) ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'agency_name', 'project_title', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE STRICT AI ENGINE ---
def run_query(text, prompt, persona="Simple Assistant"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": f"You are a {persona}. RULES: 1. NO INTROS. 2. USE VERTICAL BULLETS. 3. BE VERY SHORT. 4. SIMPLE WORDS ONLY."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:20000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Busy. Try again."

# --- 3. UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        for k in list(st.session_state.keys()):
            if k != 'total_saved': del st.session_state[k]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- THE CLEAN HEADER (ONLY 4 ITEMS) ---
    if not st.session_state.agency_name:
        with st.status("🏗️ Analyzing..."):
            st.session_state.agency_name = run_query(doc, "Agency Name?")
            st.session_state.project_title = run_query(doc, "Project Title?")
            st.session_state.detected_due_date = run_query(doc, "Deadline Date?")
            st.session_state.status_flag = run_query(doc, "Status: OPEN or CLOSED?").upper()
        st.rerun()

    # UI Display - Very Clean
    st.success(f"● STATUS: {st.session_state.status_flag}")
    st.write(f"**📅 DEADLINE:** {st.session_state.detected_due_date}")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- THE TABS ---
    if st.session_state.analysis_mode == "Reporting":
        # COMPLIANCE MODE: Strictly for SLAs and Penalties
        st.subheader("⚖️ Compliance Requirements")
        if not st.session_state.report_ans:
            with st.status("🔍 Extracting Penalties..."):
                st.session_state.report_ans = run_query(doc, "List the required Uptime %, the specific Violations, and the Dollar Penalties/Credits.", "Contract Auditor")
        st.markdown(st.session_state.report_ans)
    
    else:
        # BID MODE: Strictly for Project Plan
        tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Winner"])
        with tabs[0]:
            if not st.session_state.summary_ans: st.session_state.summary_ans = run_query(doc, "3 simple goals of this project.")
            st.info(st.session_state.summary_ans)
        with tabs[1]:
            if not st.session_state.tech_ans: st.session_state.tech_ans = run_query(doc, "Required tools or software?")
            st.success(st.session_state.tech_ans)
        with tabs[2]:
            if not st.session_state.submission_ans: st.session_state.submission_ans = run_query(doc, "3 steps to apply.")
            st.warning(st.session_state.submission_ans)
        with tabs[3]:
            if not st.session_state.compliance_ans: st.session_state.compliance_ans = run_query(doc, "Insurance or legal rules?")
            st.error(st.session_state.compliance_ans)
        with tabs[4]:
            if not st.session_state.award_ans: st.session_state.award_ans = run_query(doc, "How do they choose the winner?")
            st.write(st.session_state.award_ans)

else:
    st.title("🏛️ Reporting Tool")
    t1, t2 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements"])
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
