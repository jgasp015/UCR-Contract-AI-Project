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

# --- 2. THE "TAXPAYER" ENGINE (STRICT SIMPLIFICATION) ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:10000] + "\n...\n" + text[-5000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are explaining a government contract to a hard-working taxpayer. 
                1. Use zero professional jargon. 
                2. If it's a long list of tech or names, summarize it into one simple sentence.
                3. Be extremely brief. Use vertical bullet points.
                4. If the data is missing, respond ONLY with 'HIDEME'."""
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

# --- 4. MAIN LOGIC ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Analyzing for taxpayers..."):
            st.session_state.agency_name = run_ai(doc, "Which city or agency is spending this money?")
            st.session_state.project_title = run_ai(doc, "In 5 words or less, what is the project?")
            st.session_state.detected_due_date = run_ai(doc, "What is the final deadline date?")
            st.session_state.status_flag = run_ai(doc, "Is this project OPEN for bids or CLOSED?")
        st.rerun()

    # THE TAXPAYER HEADER (CLEAN)
    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag: st.success(f"STATUS: {st.session_state.status_flag.upper()}")
    if st.session_state.detected_due_date: st.write(f"**📅 DUE DATE:** {st.session_state.detected_due_date}")
    if st.session_state.agency_name: st.write(f"**💰 SPENT BY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 PROJECT:** {st.session_state.project_title}")
    st.divider()

    # THE SIMPLE TABS
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        # (Auditor logic removed for brevity, uses same run_ai style)
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 The Plan", "🛠️ Tools", "📝 How to Apply", "⚖️ The Rules", "💰 How to Win"])
        with b1:
            if not st.session_state.get('summary_ans'): 
                st.session_state.summary_ans = run_ai(doc, "What is the taxpayer getting for their money? (3 simple bullets)")
            st.info(st.session_state.summary_ans if st.session_state.summary_ans else "Details not found.")
        with b2:
            if not st.session_state.get('tech_ans'): 
                st.session_state.tech_ans = run_ai(doc, "What basic tools or computers are they buying?")
            st.success(st.session_state.tech_ans if st.session_state.tech_ans else "Tools not listed.")
        with b3:
            if not st.session_state.get('submission_ans'): 
                st.session_state.submission_ans = run_ai(doc, "What are the 3 steps to apply?")
            st.warning(st.session_state.submission_ans if st.session_state.submission_ans else "Steps not found.")
        with b4:
            if not st.session_state.get('compliance_ans'): 
                st.session_state.compliance_ans = run_ai(doc, "What are the main insurance or safety rules?")
            st.error(st.session_state.compliance_ans if st.session_state.compliance_ans else "Rules not found.")
        with b5:
            if not st.session_state.get('award_ans'): 
                st.session_state.award_ans = run_ai(doc, "How do they decide who gets the money? Best price or best idea?")
            st.write(st.session_state.award_ans if st.session_state.award_ans else "Criteria not found.")

else:
    # (Initial Menu logic stays the same)
    st.title("🏛️ Reporting Tool")
    tab_bid, tab_comp, tab_url = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    # ... uploader code
