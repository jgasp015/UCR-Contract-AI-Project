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
# 3. AI ENGINE (TAXPAYER FOCUS)
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:28000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY (*). 3. EVERY BULLET ON NEW LINE. 4. BE BRIEF."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "⚠️ Service busy. Please try again."

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
    
    if not st.session_state.get("agency_name"):
        with st.status("Scanning..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Deadline Date?")
        st.rerun()

    # --- THE 3-LINE HEADER ---
    st.subheader("🏛️ Project Snapshot")
    
    # Line 1: Status
    status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
    due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
    if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
    else: st.error(f"● STATUS: {status}")

    # Line 2: Agency
    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    
    # Line 3: Project Name
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- TWO TABS ONLY ---
    t1, t2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
    
    with t1:
        st.info(run_ai(doc, "List the 'Remove' and 'Install' work tasks from the Scope of Service section."))
    
    with t2:
        st.success(run_ai(doc, "List ONLY the technology and gear being used (e.g., Laptops, 4-in-1 Antennas, Cradlepoint, Cameras, VPU, cables)."))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])

    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = extract_pdf_data(up)
            st.rerun()

    with tab2:
        st.write("Compliance section currently uses same logic - upload contract here.")
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = extract_pdf_data(up_c)
            st.rerun()
            
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...")
