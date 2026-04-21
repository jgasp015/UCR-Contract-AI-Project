import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re
import time

# --- SILO 1: SESSION STATE (PERMANENT) ---
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

def reset_analysis():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

# Initialize keys
for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
            'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
    if k not in st.session_state: st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: THE "ONE-SHOT" AI ENGINE (PREVENTS HANGING) ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": f"{system_msg} Use simple words. Bullet points only."}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        res = r.json()
        if "choices" in res:
            return res['choices'][0]['message']['content'].strip()
        return None
    except:
        return None

# --- SILO 3: UI FLOW (FAST HEADER FIX) ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text

    # THE FIX: Ask for the header in ONE request
    if not st.session_state.agency_name:
        with st.status("🏗️ Building Header...") as s:
            header_info = run_ai(doc, "Identify Agency Name, Project Title, and Deadline.", "Identify facts.")
            if header_info:
                # Store the whole chunk in Agency Name temporarily to break the loop
                st.session_state.agency_name = header_info
                st.rerun()

    st.success(f"● BID IDENTIFIED")
    st.info(st.session_state.agency_name)

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.spinner("🔍 Analyzing Compliance..."):
                st.session_state.report_ans = run_ai(doc, "Explain: Reporting, Uptime, Penalties, Stop-Clock.", "Compliance Expert.")
                st.rerun()
        st.markdown(st.session_state.report_ans)
    else:
        # TAB LOADING
        if not st.session_state.summary_ans:
            with st.status("🧠 Simplifying Tabs...") as s:
                st.session_state.summary_ans = run_ai(doc, "Simple goals and project ID.", "Mom-test.")
                st.session_state.tech_ans = run_ai(doc, "Specific Software/Hardware needed? Max 5.", "Simple list.")
                st.session_state.submission_ans = run_ai(doc, "How to apply? 1,2,3.", "Steps.")
                st.session_state.compliance_ans = run_ai(doc, "Insurance/Rules?", "Simple.")
                st.session_state.award_ans = run_ai(doc, "How to win?", "Simple.")
                s.update(label="Complete!", state="complete")
                st.rerun()

        t1, t2, t3, t4, t5 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.info(st.session_state.summary_ans); t2.success(st.session_state.tech_ans)
        t3.warning(st.session_state.submission_ans); t4.error(st.session_state.compliance_ans)
        t5.write(st.session_state.award_ans)

else:
    # --- SILO 4: MAIN MENU ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    # (Uploaders and Scanner logic remains identically protected)
