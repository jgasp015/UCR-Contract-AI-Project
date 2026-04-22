import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: 
    st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: 
    st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': 
            del st.session_state[key]
    st.session_state.active_bid_text = None
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE DATA EXTRACTION ENGINE ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Using a larger text slice to ensure we capture the middle pages
    ctx = text[:25000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """RULES:
                1. START IMMEDIATELY with the data.
                2. Use ONLY vertical bullet points (*).
                3. NO introductory filler.
                4. For 'Scope of Service', list the EXACT hardware tasks (Remove/Install).
                5. If missing, say 'HIDEME'."""
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: 
        return None

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
    
    # --- BID DOCUMENT HEADER: 3 LINES ONLY ---
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Scanning Document..."):
            st.session_state.agency_name = run_ai(doc, "Who is the City Agency spending the money?")
            st.session_state.project_title = run_ai(doc, "What is the Project Title on the cover page?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "What is the deadline date?")
        st.rerun()

    # THE 3-LINE HEADER
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")

    if st.session_state.agency_name: 
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: 
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- TABS ---
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What data must be reported?"))
        # (Other compliance tabs same as before)
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1:
            # FORCED TO EXTRACT EXACT TASKS
            st.info(run_ai(doc, "Look at Section 4. List the exact 'Remove' and 'Install' tasks line by line."))
        with b2:
            st.success(run_ai(doc, "List the specific gear like laptops, antennas, and cables."))
        with b3:
            st.warning(run_ai(doc, "3 simple steps to apply."))
        with b4:
            st.error(run_ai(doc, "Explain the 5% local rule and 10% penalty."))
        with b5:
            st.write(run_ai(doc, "How is the winner picked?"))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
