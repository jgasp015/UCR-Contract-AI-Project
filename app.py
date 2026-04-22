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

# --- 2. THE TAXPAYER ENGINE (STRICT DATA EXTRACTION) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Grab the heart of the document where the real work is described
    ctx = text[2000:20000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are explaining a government contract to a taxpayer.
                RULES:
                1. NO INTROS like 'Here is the information'.
                2. If a specific dollar amount or percentage is mentioned, include it.
                3. Describe hardware (like laptops or antennas) and penalties (like 10% deductions) clearly.
                4. Use vertical bullets (*).
                5. If missing, respond ONLY with 'HIDEME'."""
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: return "⚠️ Service busy."

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
        with st.status("🏗️ Extracting Taxpayer Facts..."):
            st.session_state.agency_name = run_ai(doc, "Who is spending the money (Agency)?")
            st.session_state.project_title = run_ai(doc, "What is being bought (5 words)?")
            st.session_state.detected_due_date = run_ai(doc, "What is the final deadline?")
            st.session_state.status_flag = run_ai(doc, "Is this OPEN or CLOSED?")
        st.rerun()

    # THE CLEAN 3-LINE HEADER
    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.detected_due_date}" if st.session_state.detected_due_date else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}{due}")

    if st.session_state.agency_name: st.write(f"**💰 SPENT BY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
    st.divider()

    # THE TABS
    if st.session_state.analysis_mode == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What data must be reported (Sales/SLA)?"))
        with t2: st.error(run_ai(doc, "What counts as a violation?"))
        with t3: st.warning(run_ai(doc, "What is the dollar penalty for failing?"))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where are reports sent?"))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 The Plan", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1: st.info(run_ai(doc, "What is the taxpayer getting for the money?"))
        with b2: st.success(run_ai(doc, "What specific gear/hardware is being bought?"))
        with b3: st.warning(run_ai(doc, "3 steps to get this job."))
        with b4: st.error(run_ai(doc, "What are the local business rules or penalties?"))
        with b5: st.write(run_ai(doc, "How do they pick the winner? Best price or best idea?"))

else:
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_up")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="comp_up")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...", key="url_in")
