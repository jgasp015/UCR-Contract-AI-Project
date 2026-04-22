import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'agency_name': None, 'project_title': None, 
        'detected_due_date': None, 'summary_ans': None, 'tech_ans': None, 
        'submission_ans': None, 'compliance_ans': None, 'award_ans': None, 
        'bid_details': None, 'report_ans': None, 'total_saved': 360
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    init_state()
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: THE "CLEAN" MOM-TEST ENGINE ---
def run_ai(text, prompt, persona_type="simple"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # STRICT INSTRUCTION: No repeating questions, no "Not listed" spam.
    system_instruction = """
    You are a helpful assistant for a busy person. 
    1. Give ONLY the final answer. 
    2. DO NOT repeat the user's question (e.g., do not say 'What is the project title?').
    3. If you can't find it, skip it or say 'Check the portal link below'.
    4. Use the 'Mom-Test': Use words a child would understand.
    5. No conversational filler like 'Here is the answer'.
    """
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:15000]}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ Service busy. Click again."

# --- SILO 3: UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.session_state.active_bid_text:
        if st.button("🏠 Home / Back"):
            hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # 1. THE HEADER (CLEANED)
    if not st.session_state.agency_name:
        with st.status("🏗️ Simplifying..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name? (One line)")
            st.session_state.project_title = run_ai(doc, "Short Project Title?")
            st.session_state.detected_due_date = run_ai(doc, "Deadline date only?")
        st.rerun()

    st.success(f"● STATUS: ACTIVE | 📅 DUE: {st.session_state.detected_due_date}")
    st.write(f"**🏛️ WHO:** {st.session_state.agency_name}")
    st.write(f"**📄 WHAT:** {st.session_state.project_title}")
    st.divider()
    
    # 2. THE TABS (MOM-FRIENDLY)
    if st.session_state.analysis_mode == "Standard":
        if not st.session_state.summary_ans:
            with st.status("🚀 Making it easy to read..."):
                st.session_state.bid_details = run_ai(doc, "List ID number and Email address only.")
                st.session_state.summary_ans = run_ai(doc, "3 simple goals of this project?")
                st.session_state.tech_ans = run_ai(doc, "What computers or software do they need?")
                st.session_state.submission_ans = run_ai(doc, "3 simple steps to apply.")
                st.session_state.compliance_ans = run_ai(doc, "What are the big rules/insurance?")
                st.session_state.award_ans = run_ai(doc, "How do they choose the winner?")
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 The Plan", "🛠️ Tools", "📝 How to Apply", "⚖️ The Rules", "💰 How to Win"])
        tabs[0].markdown(st.session_state.bid_details)
        tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans)
        tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans)
        tabs[5].write(st.session_state.award_ans)
