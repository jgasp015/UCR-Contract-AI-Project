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
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = "Standard"

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != "total_saved":
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. THE ENGINE (MOM-MODE)
# ---------------------------
def run_ai(text, prompt, mom_mode=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:45000] 
    
    system_rules = "RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY (*). 3. EVERY BULLET ON NEW LINE. 4. IF MISSING, SAY 'HIDEME'."
    
    if mom_mode:
        system_rules += " 5. IGNORE TECHNICAL TABLES AND 'YES/NO' FORMS. 6. EXPLAIN LIKE A NEIGHBOR (SIMPLE ENGLISH)."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return None if "HIDEME" in ans.upper() else ans
    except:
        return "⚠️ Scanner timed out."

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
# 4. MAIN APP LOGIC
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- MODE 1: COMPLIANCE REQUIREMENTS (FIXED FOR MOM) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2 = st.tabs(["📊 What to Report", "💊 Penalties"])
        with t1: 
            st.info(run_ai(doc, "What specific records or updates does the contractor have to send to the city? Ignore the technical 'Table 27' checklists.", mom_mode=True))
        with t2: 
            st.error(run_ai(doc, "What are the dollar fines or penalties if the contractor messes up or misses a deadline?", mom_mode=True))

    # --- MODE 2: BID DOCUMENT (LOCKED - NO CHANGES) ---
    else:
        if not st.session_state.get("agency_name"):
            with st.status("🏗️ Final Scan..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?")
                st.session_state.project_title = run_ai(doc, "Project Title?")
                st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "Deadline Date?")
            st.rerun()

        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")
        
        if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1:
            st.info(run_ai(doc, "List the actual work tasks (like Remove/Install) line by line. Be specific."))
        with b2:
            st.success(run_ai(doc, "List ONLY the technology names and hardware mentioned (Laptops, Antennas, Cameras, etc.) line by line."))

else:
    # --- START SCREEN ---
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            reader = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            reader = PdfReader(up_c)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste portal link here...", key="url_in")
