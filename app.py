import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.session_state.active_bid_text = None
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. ENGINE (TAXPAYER MODE) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:10000] + "\n...\n" + text[-5000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "Explain this to a blue-collar taxpayer. Use vertical bullets. No jargon. Be brief. If missing, say 'HIDEME'."
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
    
    # ANALYSIS HEADER
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Analyzing for taxpayers..."):
            st.session_state.agency_name = run_ai(doc, "Which city or agency is spending this money?")
            st.session_state.project_title = run_ai(doc, "In 5 words or less, what is the project?")
            st.session_state.detected_due_date = run_ai(doc, "What is the final deadline date?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
        st.rerun()

    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag: st.success(f"STATUS: {st.session_state.status_flag.upper()}")
    if st.session_state.detected_due_date: st.write(f"**📅 DUE DATE:** {st.session_state.detected_due_date}")
    if st.session_state.agency_name: st.write(f"**💰 SPENT BY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
    st.divider()

    # THE TABS
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Penalties", "📅 Frequency"])
        with t1:
            st.info(run_ai(doc, "What specific data do they need to report?"))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1:
            st.info(run_ai(doc, "What are the 3 main goals?"))
        with b2:
            st.success(run_ai(doc, "What basic tools are they buying?"))
        with b3:
            st.warning(run_ai(doc, "3 steps to apply?"))
        with b4:
            st.error(run_ai(doc, "Main insurance/safety rules?"))
        with b5:
            st.write(run_ai(doc, "How do they pick the winner?"))

else:
    # --- RESTORED MAIN MENU ---
    st.title("🏛️ Reporting Tool")
    tab_bid, tab_comp, tab_url = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    
    with tab_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with tab_comp:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with tab_url:
        u_in = st.text_input("Agency URL:", placeholder="Paste portal link here...", key="url_in")
        if st.button("Scan Portal"):
            st.info("Scanner results will appear here after scanning.")
