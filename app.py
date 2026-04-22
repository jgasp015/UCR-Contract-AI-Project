import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE ENGINE ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Using a larger window to ensure page 5 (Scope) is always included
    ctx = text[:28000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """RULES: 
                1. NO INTROS. 
                2. Use ONLY vertical bullet points (*). 
                3. Put EVERY bullet point on a NEW LINE. 
                4. For 'Scope of Service', you MUST list every line that starts with 'Remove' or 'Install'.
                5. If missing, say 'HIDEME'."""
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
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- BID DOCUMENT HEADER (3 LINES ONLY) ---
    if not st.session_state.get('agency_name'):
        with st.status("Scanning..."): # Removed "For Mom" text
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Deadline Date?")
        st.rerun()

    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")

    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # --- TABS ---
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "List specifically what data must be reported line by line."))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1:
            # FORCED TO CAPTURE "REMOVE" AND "INSTALL"
            st.info(run_ai(doc, "Find the 'Scope of Service' section. List every single item that needs to be 'Removed' and every single item that needs to be 'Installed' line by line."))
        with b2:
            st.success(run_ai(doc, "List the hardware like laptops, antennas, and cables line by line."))
        with b3:
            st.warning(run_ai(doc, "3 simple steps to apply via PlanetBids."))
        with b4:
            st.error(run_ai(doc, "Explain the 5% local business rule and the 10% penalty."))
        with b5:
            st.write(run_ai(doc, "How do they pick the winner?"))

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
