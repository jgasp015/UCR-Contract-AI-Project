import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (PRESERVED) ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'agency_name', 'project_title', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE STRICTOR ENGINE ---
def deep_query(full_text, specific_prompt, persona="Contract-Coach"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": f"""You are a {persona}. 
                STRICT RULES: 
                1. START IMMEDIATELY with a bullet point (*).
                2. NO introductory text (NEVER say 'Here are the points').
                3. NO conversational filler.
                4. EVERY point must be on a new line.
                5. Use simple words for a beginner."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:25000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Service busy. Click again."

# --- 3. UI FLOW ---
st.title("🏛️ Reporting Tool")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        for k in list(st.session_state.keys()):
            if k != 'total_saved': del st.session_state[k]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- COMPLIANCE REQUIREMENTS ---
    if st.session_state.analysis_mode == "Reporting":
        st.header("⚖️ Compliance Requirements")
        if not st.session_state.report_ans:
            with st.status("🔍 Extracting..."):
                prompt = "List the Target Uptime, Violation definitions, Financial Penalties, and Reporting Deadlines."
                st.session_state.report_ans = deep_query(doc, prompt, persona="SLA-Auditor")
        st.markdown(st.session_state.report_ans)
    
    # --- BID DOCUMENT ---
    else:
        if not st.session_state.agency_name:
            with st.status("🏗️ Reading..."):
                st.session_state.agency_name = deep_query(doc, "Agency Name?", "Data-Finder")
                st.session_state.project_title = deep_query(doc, "Project Title?", "Data-Finder")
                st.session_state.detected_due_date = deep_query(doc, "Deadline date?", "Data-Finder")
                st.session_state.status_flag = deep_query(doc, "Status: OPEN or CLOSED?", "Data-Finder").upper()
            st.rerun()

        st.success(f"● STATUS: {st.session_state.status_flag} | 📅 DUE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID:** {st.session_state.project_title}")
        st.divider()

        tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Winner"])
        with tabs[0]:
            if not st.session_state.summary_ans: 
                st.session_state.summary_ans = deep_query(doc, "3 simple goals.")
            st.info(st.session_state.summary_ans)
        with tabs[1]:
            if not st.session_state.tech_ans: 
                st.session_state.tech_ans = deep_query(doc, "Required tools?")
            st.success(st.session_state.tech_ans)
        with tabs[2]:
            if not st.session_state.submission_ans: 
                st.session_state.submission_ans = deep_query(doc, "3 steps to apply.")
            st.warning(st.session_state.submission_ans)
        with tabs[3]:
            if not st.session_state.compliance_ans: 
                st.session_state.compliance_ans = deep_query(doc, "Insurance and legal rules?")
            st.error(st.session_state.compliance_ans)
        with tabs[4]:
            if not st.session_state.award_ans: 
                st.session_state.award_ans = deep_query(doc, "How do you win?")
            st.write(st.session_state.award_ans)
else:
    # (Main Menu Tabs remain the same)
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="up_bid_final")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="up_comp_final")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
