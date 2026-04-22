import streamlit as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE & RESET (UNTOUCHED)
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
# 2. THE CLEAN ENGINE
# ---------------------------
def run_ai(text, prompt, is_compliance=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:60000] 
    
    if is_compliance:
        # COMPLIANCE RULES - UNTOUCHED PER ORDER
        system_rules = """RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY (*). 3. EVERY BULLET ON NEW LINE. 
        4. YOU ARE A COMPLIANCE AUDITOR. 5. FIND EVERY SINGLE SLA: Availability, Time to Repair, Provisioning, and Notification. 
        6. LIST WHAT QUALIFIES AS 'NON-COMPLIANT' OR A 'FAILURE'. 7. IGNORE Table 27.2 checklists. 8. USE SIMPLE ENGLISH."""
    else:
        # BID RULES - NEW "FACTS ONLY" LOGIC TO STOP THE LOOPING
        system_rules = "You are a data extractor. Return ONLY a vertical bulleted list of facts. No conversation. No repeating the prompt."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"Text: {ctx}\n\nTask: {prompt}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=35)
        ans = r.json()["choices"][0]["message"]["content"].strip()
        # Kill the loop if it tries to echo the prompt
        if len(ans) > 500 and ans.count("*") > 20 and "Remove all" in ans:
            return "Scan failed to find unique data. Please check the document pages."
        return ans if ans else "Data not found."
    except:
        return "⚠️ Scanner timed out."

# ---------------------------
# 3. SIDEBAR (UNTOUCHED)
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
    
    # --- COMPLIANCE MODE (UNTOUCHED) ---
    if st.session_state.analysis_mode == "Reporting":
        t1, t2 = st.tabs(["📊 SLA & Non-Compliance", "💊 Penalties"])
        with t1: 
            st.info(run_ai(doc, "List all Service Level Agreements (SLA) and exactly what makes a contractor 'Non-Compliant'.", is_compliance=True))
        with t2: 
            st.error(run_ai(doc, "List every dollar fine or penalty mentioned for failing an SLA.", is_compliance=True))

    # --- BID DOCUMENT MODE (HEADER FIXED + LOOP-FREE TABS) ---
    else:
        if not st.session_state.get("agency_name"):
            with st.status("🏗️ Scanning..."):
                st.session_state.agency_name = run_ai(doc, "What is the Agency name?")
                st.session_state.project_title = run_ai(doc, "What is the Project Title?")
                st.session_state.status_flag = run_ai(doc, "Is the bid OPEN or CLOSED?")
                st.session_state.due_date = run_ai(doc, "What is the deadline date?")
            st.rerun()

        # 3-LINE HEADER
        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status: st.success(f"● STATUS: {status}{due}")
        else: st.error(f"● STATUS: {status}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        st.divider()

        # BID TABS
        b1, b2 = st.tabs(["📖 Scope of Work", "🛠️ Specifications"])
        with b1:
            st.info(run_ai(doc, "List the 'Remove' and 'Install' tasks from the Scope of Service section. Do not include rules or legal text."))
        with b2:
            st.success(run_ai(doc, "List ONLY the hardware, technology, and gear names (Laptops, Antennas, Cradlepoint, etc.) mentioned."))

else:
    # --- START SCREEN (UNTOUCHED) ---
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            reader = PdfReader(up)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            reader = PdfReader(up_c)
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with tab3:
        st.text_input("Agency URL:", placeholder="Paste portal link here...", key="url_in")
