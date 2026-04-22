import re
import streamlit as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE INITIALIZATION
# ---------------------------
if "total_saved" not in st.session_state:
    st.session_state.total_saved = 480
if "active_bid_text" not in st.session_state:
    st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != "total_saved":
            del st.session_state[key]
    st.session_state.active_bid_text = None
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. PDF HELPER
# ---------------------------
def extract_pdf_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    full_text_parts = []
    for page in reader.pages:
        txt = page.extract_text() or ""
        full_text_parts.append(txt)
    return "\n".join(full_text_parts)

# ---------------------------
# 3. AI ENGINE (ULTRA-SIMPLE)
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:28000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY (*). 3. EVERY BULLET ON NEW LINE. 4. IF MISSING, SAY 'HIDEME'."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return None if "HIDEME" in ans.upper() else ans
    except:
        return None

# ---------------------------
# 4. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# ---------------------------
# 5. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # ONE-TIME DATA EXTRACTION
    if not st.session_state.get("agency_name"):
        with st.status("Scanning..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Deadline Date?")
        st.rerun()

    # --- THE 3-LINE HEADER ---
    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        header = f"● {status}"
        if st.session_state.due_date: header += f" | DUE: {st.session_state.due_date}"
        if "OPEN" in status: st.success(header)
        else: st.error(header)

    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 PROJECT NAME:** {st.session_state.project_title}")
    st.divider()

    # --- TWO TABS ONLY ---
    t1, t2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
    
    with t1:
        st.info(run_ai(doc, "List the exact 'Remove' and 'Install' tasks from the Scope of Service section."))
    
    with t2:
        st.success(run_ai(doc, "List the specific gear like laptops, antennas, and cables mentioned in section 4."))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])

    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = extract_pdf_data(up)
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = extract_pdf_data(up_c)
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"): st.info("Results will appear here.")
