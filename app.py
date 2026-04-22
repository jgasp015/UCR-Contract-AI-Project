import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.session_state.active_bid_text = None
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. ENGINE (TAXPAYER MODE) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Scan the first 15k characters where titles, scope, and dates live
    ctx = text[:15000]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """Explain this to a blue-collar taxpayer. 
                1. Use ONLY vertical bullets (*). 
                2. NO introductory sentences. 
                3. Be extremely brief. 
                4. If missing, say 'HIDEME'."""
            },
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

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # 3-LINE HEADER (STATUS, AGENCY, BID NAME)
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Scanning for Taxpayer Facts..."):
            st.session_state.agency_name = run_ai(doc, "Who is the City or Agency spending the money?")
            st.session_state.project_title = run_ai(doc, "What is the Project Title found on the cover?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "What is the 'RFP Due by' date and time?")
        st.rerun()

    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")

    if st.session_state.agency_name: st.write(f"**💰 SPENT BY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # TABS (PLAN REPLACED WITH SCOPE OF SERVICE)
    if st.session_state.get('analysis_mode') == "Reporting":
        # (LOCKED - NO TOUCHING COMPLIANCE SECTION)
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What specific data (sales, uptime, etc.) must be reported?"))
        with t2: st.error(run_ai(doc, "What exactly counts as a violation or SLA breach?"))
        with t3: st.warning(run_ai(doc, "What are the specific dollar penalties or remedies?"))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where or how are the reports submitted?"))
    else:
        # BID DOCUMENT TABS
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1:
            st.info(run_ai(doc, "What is the 'Scope of Service'? (Explain what hardware is being removed and installed in 3 bullets)"))
        with b2:
            st.success(run_ai(doc, "What specific gear (laptops, antennas, cables) is being bought?"))
        with b3:
            st.warning(run_ai(doc, "What are the 3 steps to get this job?"))
        with b4:
            st.error(run_ai(doc, "Explain the 5% local business rule and the 10% deduction penalty."))
        with b5:
            st.write(run_ai(doc, "How do they pick the winner? (Points for experience vs price)"))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"): st.info("Results will appear here.")
