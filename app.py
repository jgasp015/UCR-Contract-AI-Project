import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE INITIALIZATION ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. ENGINE (STRICT PERSONA) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Context window optimized to see headers and footers (where dates hide)
    ctx = text[:12000] + "\n...\n" + text[-8000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant. RULES: 1. NO INTROS. 2. USE VERTICAL BULLETS. 3. BE EXTREMELY BRIEF. 4. IF DATA IS MISSING, SAY 'HIDEME'."
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
        for key in list(st.session_state.keys()):
            if key != 'total_saved': del st.session_state[key]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- MODE 1: COMPLIANCE REQUIREMENTS (LOCKED - NO TOUCHING) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What specific data (sales, uptime, etc.) must the contractor report?"))
        with t2: st.error(run_ai(doc, "What exactly counts as a violation or SLA breach?"))
        with t3: st.warning(run_ai(doc, "What are the specific dollar penalties or remedies?"))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where or how are the reports submitted?"))
            
    # --- MODE 2: BID DOCUMENT (HEADER UPDATED) ---
    else:
        if not st.session_state.get('agency_name'):
            with st.status("🏗️ Scanning..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name (short)?")
                st.session_state.project_title = run_ai(doc, "Project Title (short)?")
                st.session_state.status_flag = run_ai(doc, "Status: OPEN or CLOSED?")
                st.session_state.detected_due_date = run_ai(doc, "Final deadline date?")
            st.rerun()

        # CLEAN 3-LINE HEADER
        if st.session_state.status_flag:
            status_txt = st.session_state.status_flag.upper()
            due_txt = f" | DUE: {st.session_state.detected_due_date}" if ("OPEN" in status_txt and st.session_state.detected_due_date) else ""
            if "OPEN" in status_txt:
                st.success(f"● STATUS: {status_txt}{due_txt}")
            else:
                st.error(f"● STATUS: {status_txt}")

        if st.session_state.agency_name:
            st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
            
        if st.session_state.project_title:
            st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
        
        st.divider()

        # TABS (PRESERVED)
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Award"])
        with b1: st.info(run_ai(doc, "3 simple goals."))
        with b2: st.success(run_ai(doc, "Basic tools needed."))
        with b3: st.warning(run_ai(doc, "3 steps to apply."))
        with b4: st.error(run_ai(doc, "Main insurance/legal rules."))
        with b5: st.write(run_ai(doc, "How is the winner picked?"))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up_final")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up_final")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...", key="url_in_final")
        if st.button("Scan Portal"):
            st.info("Scanner results will appear here.")
