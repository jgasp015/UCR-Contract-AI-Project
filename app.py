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
# 2. THE CLEAN ENGINE
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Single deep slice of text
    ctx = text[:25000] 
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
# 3. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()

# ---------------------------
# 4. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # ONE-TIME DATA PULL
    if not st.session_state.get("agency_name"):
        with st.status("Scanning..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Deadline Date?")
        st.rerun()

    # --- THE 3-LINE HEADER ---
    st.subheader("🏛️ Project Snapshot")
    
    # 1. Status
    status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
    due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
    if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
    else: st.error(f"● STATUS: {status}")

    # 2. Agency
    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    
    # 3. Project Name
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- TWO TABS ONLY ---
    t1, t2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
    
    with t1:
        st.info(run_ai(doc, "List the 'Remove' and 'Install' tasks from the document line by line."))
    
    with t2:
        st.success(run_ai(doc, "List ONLY the specific technology names like Camera, Laptop, Cradlepoint, etc."))

else:
    # START SCREEN
    st.title("🏛️ Reporting Tool")
    up = st.file_uploader("Upload Bid PDF", type="pdf")
    if up:
        reader = PdfReader(up)
        st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
        st.rerun()
