import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE INITIALIZATION ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

# --- 2. ENGINE (STRICT PERSONA) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Skip the first few pages of "legal fluff" and read the heart of the document
    ctx = text[5000:25000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant. RULES: 1. NO INTROS. 2. USE VERTICAL BULLETS. 3. SUMMARIZE DATA INTO SIMPLE TERMS. 4. IF DATA IS MISSING, SAY 'Not found in document'."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Service busy. Click again."

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    # FIXED: Button no longer triggers the yellow error
    if st.button("🏠 Home / Reset App"):
        for key in list(st.session_state.keys()):
            if key != 'total_saved': del st.session_state[key]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- COMPLIANCE MODE (NO HEADER) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1:
            st.info(run_ai(doc, "What specific data (sales, uptime, etc.) must the contractor report?"))
        with t2:
            st.error(run_ai(doc, "What exactly counts as a violation or SLA breach?"))
        with t3:
            st.warning(run_ai(doc, "What are the specific dollar penalties or remedies?"))
        with t4:
            st.success(run_ai(doc, "How often are reports due? (Monthly/Quarterly)"))
        with t5:
            st.write(run_ai(doc, "Where or how are the reports submitted?"))
            
    # --- BID MODE (CLEAN 3-LINE HEADER) ---
    else:
        if not st.session_state.get('agency_name'):
            st.session_state.agency_name = run_ai(doc, "Agency Name (short)?")
            st.session_state.project_title = run_ai(doc, "Project Title (short)?")
            st.session_state.status_flag = run_ai(doc, "Is this OPEN or CLOSED?")
            st.rerun()

        st.success(f"● STATUS: {st.session_state.status_flag}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
        st.divider()

        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Win"])
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
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"):
            st.info("Scanner results will appear here.")
