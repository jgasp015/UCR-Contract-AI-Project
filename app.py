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

# --- 2. ENGINE (ULTRA-STRICT FOR MOTHER) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:12000] + "\n...\n" + text[-5000:]
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
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: return None

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.button("🏠 Home / Reset App", on_click=hard_reset)
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- MODE A: COMPLIANCE REQUIREMENTS (TABS ONLY - NO HEADER) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What specific data (sales, uptime, etc.) must be reported?"))
        with t2: st.error(run_ai(doc, "What counts as a violation or SLA breach?"))
        with t3: st.warning(run_ai(doc, "What are the specific dollar penalties or remedies?"))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where or how are the reports submitted?"))

    # --- MODE B: BID DOCUMENT (3-LINE HEADER ONLY) ---
    else:
        if not st.session_state.get('agency_name'):
            with st.status("🏗️ Scanning..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?")
                st.session_state.project_title = run_ai(doc, "Project Title (short)?")
                st.session_state.status_flag = run_ai(doc, "Is it OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "Deadline Date?")
            st.rerun()

        # THE 3-LINE HEADER
        if st.session_state.status_flag:
            status = st.session_state.status_flag.upper()
            due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
            if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
            else: st.error(f"● STATUS: {status}")

        if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        # TABS
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1: st.info(run_ai(doc, "3 simple goals of this project."))
        with b2: st.success(run_ai(doc, "Basic tools needed."))
        with b3: st.warning(run_ai(doc, "3 steps to apply."))
        with b4: st.error(run_ai(doc, "Main insurance or legal rules."))
        with b5: st.write(run_ai(doc, "How do they pick the winner?"))

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
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...", key="url_in")
