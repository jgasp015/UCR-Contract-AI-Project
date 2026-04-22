import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE INITIALIZATION ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE FAST-SCAN ENGINE ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] # Single focused slice for speed
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a helpful assistant. RULES: 1. NO INTROS. 2. USE VERTICAL BULLETS (*). 3. BE EXTREMELY BRIEF. 4. IF MISSING, SAY 'HIDEME'."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
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

    # ONE-TIME DEEP SCAN (Makes tabs instant)
    if not st.session_state.get('agency_name'):
        with st.status("🚀 Fast Scanning Document..."):
            # Header info
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Short Project Title?")
            st.session_state.status_flag = run_ai(doc, "Status: OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Final deadline date?")
            
            if st.session_state.get('analysis_mode') == "Reporting":
                # Compliance logic
                st.session_state.rep_ans = run_ai(doc, "List Uptime %, Violations, Penalties, and Due Dates.")
            else:
                # Bid logic
                st.session_state.summary_ans = run_ai(doc, "3 simple goals.")
                st.session_state.tech_ans = run_ai(doc, "Basic tools needed.")
                st.session_state.submission_ans = run_ai(doc, "3 steps to apply.")
                st.session_state.compliance_ans = run_ai(doc, "Insurance/Legal rules.")
                st.session_state.award_ans = run_ai(doc, "How do they choose the winner?")
        st.rerun()

    # --- CLEAN 3-LINE HEADER ---
    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")

    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
    st.divider()

    # --- TABS (INSTANT LOADING) ---
    if st.session_state.analysis_mode == "Reporting":
        st.header("📊 Compliance Requirements")
        st.info(st.session_state.rep_ans if st.session_state.rep_ans else "Reporting rules not found.")
    else:
        t1, t2, t3, t4, t5 = st.tabs(["📖 Plan", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        t1.info(st.session_state.summary_ans if st.session_state.summary_ans else "No goals found.")
        t2.success(st.session_state.tech_ans if st.session_state.tech_ans else "No tools found.")
        t3.warning(st.session_state.submission_ans if st.session_state.submission_ans else "No steps found.")
        t4.error(st.session_state.compliance_ans if st.session_state.compliance_ans else "No rules found.")
        t5.write(st.session_state.award_ans if st.session_state.award_ans else "No winner info found.")

else:
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal"): st.info("Results will appear here.")
