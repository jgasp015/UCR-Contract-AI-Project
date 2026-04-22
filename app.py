import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE FAST ENGINE ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # We take a specific slice to ensure speed
    ctx = text[:25000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "RULES: 1. NO INTROS. 2. VERTICAL BULLETS. 3. BE EXTREMELY BRIEF. 4. IF MISSING, SAY 'HIDEME'."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=25)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: return None

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- MODE A: COMPLIANCE REQUIREMENTS (TABS ONLY) ---
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "List specifically what data must be reported line by line."))
        with t2: st.error(run_ai(doc, "List what counts as a violation line by line."))
        with t3: st.warning(run_ai(doc, "List dollar penalties line by line."))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where are reports sent?"))

    # --- MODE B: BID DOCUMENT (3-LINE HEADER ONLY) ---
    else:
        # ONE-TIME FAST SCAN
        if not st.session_state.get('agency_name'):
            with st.status("⚡ Fast-Scanning for Mom..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?")
                st.session_state.project_title = run_ai(doc, "Project Title?")
                st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "Deadline Date?")
            st.rerun()

        st.subheader("🏛️ Project Snapshot")
        if st.session_state.status_flag:
            status = st.session_state.status_flag.upper()
            due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
            if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
            else: st.error(f"● STATUS: {status}")

        if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1: st.info(run_ai(doc, "List the 'Remove' and 'Install' tasks from Section 4 line by line."))
        with b2: st.success(run_ai(doc, "List the hardware like laptops and antennas line by line."))
        with b3: st.warning(run_ai(doc, "3 simple steps to apply."))
        with b4: st.error(run_ai(doc, "Explain the 5% local rule and 10% penalty."))
        with b5: st.write(run_ai(doc, "How do they pick the winner?"))

else:
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
