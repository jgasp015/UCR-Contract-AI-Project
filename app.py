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

# --- 2. ENGINE (ULTRA-STRICT) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:10000] + "\n...\n" + text[-5000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "STRICT RULES: 1. NO INTRODUCTIONS. 2. NO FILLER. 3. START IMMEDIATELY WITH THE DATA. 4. IF MISSING, SAY 'HIDEME'."
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
    
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Scanning..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title (short)?")
            st.session_state.detected_due_date = run_ai(doc, "Deadline Date?")
            st.session_state.status_flag = run_ai(doc, "Is it OPEN or CLOSED?")
        st.rerun()

    # --- THE CLEAN 3-LINE HEADER (TAXPAYER STYLE) ---
    st.subheader("🏛️ Project Overview")
    
    # Line 1: Status + Due Date
    if st.session_state.status_flag:
        status_txt = st.session_state.status_flag.upper()
        due_txt = f" | DUE: {st.session_state.detected_due_date}" if st.session_state.detected_due_date else ""
        if "OPEN" in status_txt:
            st.success(f"● {status_txt}{due_txt}")
        else:
            st.error(f"● {status_txt}{due_txt}")

    # Line 2: Agency
    if st.session_state.agency_name:
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        
    # Line 3: Project Name
    if st.session_state.project_title:
        st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
    
    st.divider()

    # THE TABS
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1:
            st.info(run_ai(doc, "What specific data needs reporting? (List only)"))
        with t2:
            st.error(run_ai(doc, "What counts as a violation? (List only)"))
        with t3:
            st.warning(run_ai(doc, "What are the penalties? (List only)"))
        with t4:
            st.success(run_ai(doc, "How often are reports due?"))
        with t5:
            st.write(run_ai(doc, "Where/how to submit?"))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1:
            st.info(run_ai(doc, "3 simple goals of this project."))
        with b2:
            st.success(run_ai(doc, "Basic tools needed."))
        with b3:
            st.warning(run_ai(doc, "3 steps to apply."))
        with b4:
            st.error(run_ai(doc, "Main insurance or legal rules."))
        with b5:
            st.write(run_ai(doc, "How is the winner picked?"))

else:
    st.title("🏛️ Reporting Tool")
    tab_bid, tab_comp, tab_url = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
            
    with tab_comp:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
            
    with tab_url:
        u_in = st.text_input("Agency URL:", placeholder="Paste portal link here...")
        if st.button("Scan Portal"):
            st.info("Scanner results will appear here.")
