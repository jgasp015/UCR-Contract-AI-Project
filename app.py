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
# 2. UNIVERSAL SCAN ENGINE
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:40000] 
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
    
    # --- MODE 1: COMPLIANCE REQUIREMENTS (TABS ONLY - NO HEADER) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "List specifically what data or metrics must be reported line by line."))
        with t2: st.error(run_ai(doc, "List exactly what counts as a violation or breach line by line."))
        with t3: st.warning(run_ai(doc, "List the specific dollar penalties or remedies line by line."))
        with t4: st.success(run_ai(doc, "How often are reports due? List frequencies line by line."))
        with t5: st.write(run_ai(doc, "Where or how are the reports submitted?"))

    # --- MODE 2: BID DOCUMENT (3-LINE HEADER + 2 TABS) ---
    else:
        if not st.session_state.get("agency_name"):
            with st.status("Scanning..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?")
                st.session_state.project_title = run_ai(doc, "Project Title?")
                st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "Deadline Date?")
            st.rerun()

        # 3-LINE HEADER
        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")
        if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        # 2 TABS ONLY
        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1:
            st.info(run_ai(doc, "Find the Scope of Work. List every task (like Remove/Install) line by line. Be specific to the hardware mentioned."))
        with b2:
            st.success(run_ai(doc, "List ONLY the technology and equipment names mentioned (Laptops, Antennas, Cameras, etc.) line by line."))

else:
    # --- START SCREEN (STRICT SEPARATION) ---
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
