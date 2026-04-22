import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def hard_reset():
    keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 
            'rep_what', 'rep_viol', 'rep_rem', 'rep_freq', 'rep_admin', 'status_flag', 
            'agency_name', 'project_title', 'detected_due_date']
    for k in keys: st.session_state[k] = None
    st.session_state.active_bid_text = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. THE CLEAN ENGINE ---
def run_ai(text, prompt, persona="Simple Assistant"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # We now grab the first 10k and last 10k characters (where dates usually hide)
    ctx = text[:10000] + "\n...[CONTENT SKIP]...\n" + text[-10000:]
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"You are a {persona}. RULES: 1. NO INTROS. 2. USE BULLETS. 3. IF DATA IS MISSING, RESPOND WITH THE WORD 'HIDEME'."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0 
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except: return None

# --- 3. UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset"):
        hard_reset(); st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    if not st.session_state.get('agency_name'):
        with st.status("🏗️ Scanning Document..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?", "Data Finder")
            st.session_state.project_title = run_ai(doc, "Project Title?", "Data Finder")
            st.session_state.detected_due_date = run_ai(doc, "Final Deadline Date?", "Data Finder")
            st.session_state.status_flag = run_ai(doc, "Status: OPEN or CLOSED?", "Data Finder")
        st.rerun()

    # --- THE "HIDEME" LOGIC: ONLY SHOW IF DATA EXISTS ---
    if st.session_state.status_flag:
        st.success(f"● STATUS: {st.session_state.status_flag.upper()}")
    
    if st.session_state.detected_due_date:
        st.write(f"**📅 DUE:** {st.session_state.detected_due_date}")
    
    if st.session_state.agency_name:
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        
    if st.session_state.project_title:
        st.write(f"**📄 BID:** {st.session_state.project_title}")
    
    st.divider()

    # TABS (STAYING EXACTLY THE SAME)
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin Rules"])
        # ... (reporting logic stays the same)
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Award"])
        with b1:
            if not st.session_state.get('summary_ans'): st.session_state.summary_ans = run_ai(doc, "3 goals.", "Translator")
            st.info(st.session_state.summary_ans if st.session_state.summary_ans else "Goal details not found.")
        with b2:
            if not st.session_state.get('tech_ans'): st.session_state.tech_ans = run_ai(doc, "Tools?", "Tech Expert")
            st.success(st.session_state.tech_ans if st.session_state.tech_ans else "Technical list not found.")
        with b3:
            if not st.session_state.get('submission_ans'): st.session_state.submission_ans = run_ai(doc, "Steps?", "Coach")
            st.warning(st.session_state.submission_ans if st.session_state.submission_ans else "Submission steps not found.")
        with b4:
            if not st.session_state.get('compliance_ans'): st.session_state.compliance_ans = run_ai(doc, "Legal/Insurance?", "Lawyer")
            st.error(st.session_state.compliance_ans if st.session_state.compliance_ans else "Compliance rules not found.")
        with b5:
            if not st.session_state.get('award_ans'): st.session_state.award_ans = run_ai(doc, "How to win?", "Judge")
            st.write(st.session_state.award_ans if st.session_state.award_ans else "Award criteria not found.")

else:
    st.title("🏛️ Reporting Tool")
    # ... (uploader logic)
