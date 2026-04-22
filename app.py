import streamlit as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE & RESET
# ---------------------------
if "total_saved" not in st.session_state:
    st.session_state.total_saved = 480
if "active_bid_text" not in st.session_state:
    st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != "total_saved":
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. UNIVERSAL SCAN ENGINE
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Large context window (40k chars) to find scope/specs on any page
    ctx = text[:40000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a contract auditor. 
                RULES: 
                1. NO INTROS. 
                2. Use ONLY vertical bullet points (*). 
                3. Put EVERY bullet point on a NEW LINE. 
                4. If you cannot find the specific info, say 'Not found in this document.'"""
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "⚠️ Scanner timed out. Please try again."

# ---------------------------
# 3. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# ---------------------------
# 4. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # ONE-TIME DATA PULL (3-LINE HEADER)
    if not st.session_state.get("agency_name"):
        with st.status("🏗️ Scanning All Pages..."):
            st.session_state.agency_name = run_ai(doc, "Which City, County, or State agency is spending this money?")
            st.session_state.project_title = run_ai(doc, "What is the full Project Name or Bid Title?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "What is the final deadline date and time?")
        st.rerun()

    # --- THE 3-LINE HEADER ---
    st.subheader("🏛️ Project Snapshot")
    status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
    due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
    
    if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
    else: st.error(f"● STATUS: {status}")

    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- THE TWO CORE TABS ---
    t1, t2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
    with t1:
        st.info(run_ai(doc, "Find the section describing the work to be done (Scope). List the specific tasks or labor required line by line."))
    with t2:
        st.success(run_ai(doc, "Find the technical requirements. List ONLY the specific equipment, hardware, or technology being purchased line by line."))

else:
    # --- START SCREEN (RESTORED ALL OPTIONS) ---
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab1:
        up = st.file_uploader("Upload ANY Bid PDF", type="pdf", key="u1")
        if up:
            reader = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with tab2:
        st.write("Upload a contract to see reporting and compliance rules.")
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            reader = PdfReader(up_c)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste portal link here...")
        st.button("Scan Portal")
