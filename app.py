import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime

# --- 1. SESSION STATE ---
def init_state():
    keys = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'analysis_mode': "Standard",
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None,
        'report_ans': None, 'total_saved': 0
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 GROQ_API_KEY missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, persona="General", is_header=False):
    """Unified AI Engine with Persona Switching."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if persona == "Reporting":
        system_content = "You are a senior Government Procurement and Reporting Analyst. You specialize in Technical Qualifiers, SLA triggers, and SOW compliance. Provide audit-ready data in simple vertical bullet points."
    else:
        system_content = "You are a Government Data Extractor. Today is April 20, 2026. RULES: No greetings. No intros. Bullet points only. Max 8 words per line."
    
    if is_header:
        system_content = "Respond with ONLY the name requested. Zero extra words."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:12000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        if is_header:
            return res.split('\n')[0].replace("Agency:", "").replace("Project:", "").strip()
        return res
    except: return "N/A"

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.metric("Time Saved", f"{st.session_state.total_saved}m")
    if st.button("🏠 Home / New Search"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # --- SILENT HEADER EXTRACTION ---
    if not st.session_state.agency_name:
        with st.status("Analyzing Document Context..."):
            st.session_state.agency_name = deep_query(doc, "Agency name?", is_header=True)
            st.session_state.project_title = deep_query(doc, "Project title?", is_header=True)
            raw_date = deep_query(doc, "Deadline MM/DD/YYYY?", is_header=True)
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except: st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- TOP HEADER ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.subheader(st.session_state.project_title)
    st.write(f"**{st.session_state.agency_name}**")
    st.divider()

    # --- WORKFLOW SWITCHER ---
    
    # WORKFLOW A: REPORTING MODE (Original Logic Restored)
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Extracting Technical Qualifiers & SLA Triggers..."):
                prompt = """
                Extract SLA Technical Qualifiers from this SOW:
                1. Triggers for Availability vs. Unavailable Time.
                2. Excessive Outage duration thresholds.
                3. Catastrophic Outage (CAT 2 or CAT 3) definitions.
                4. Valid 'Stop Clock' conditions.
                Use simple words for a regular citizen. Vertical bullet points only.
                """
                st.session_state.report_ans = deep_query(doc, prompt, persona="Reporting")
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Senior Analyst: Reporting & Compliance Snapshot")
        st.markdown(st.session_state.report_ans)

    # WORKFLOW B: STANDARD BID MODE (Mom-friendly Logic)
    else:
        if not st.session_state.summary_ans:
            with st.status("Simplifying for citizens..."):
                st.session_state.bid_details = deep_query(doc, "ID number, Buyer name, and Email.")
                st.session_state.summary_ans = deep_query(doc, "What are the 5 main things they want to do? 1 line each.")
                st.session_state.tech_ans = deep_query(doc, "Computers or software needed? 1 line each.")
                st.session_state.submission_ans = deep_query(doc, "Simple steps to sign up.")
                st.session_state.compliance_ans = deep_query(doc, "Main 3 rules to follow (Simple words).")
                st.session_state.award_ans = deep_query(doc, "How they pick the winner?")
                st.session_state.total_saved += 120
                st.rerun()

        t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t_det.markdown(st.session_state.bid_details)
        t_plan.info(st.session_state.summary_ans)
        t_tech.success(st.session_state.tech_ans)
        t_apply.warning(st.session_state.submission_ans)
        t_legal.error(st.session_state.compliance_ans)
        t_award.write(st.session_state.award_ans)

# --- HOME VIEW ---
else:
    t1, t2, t3 = st.tabs(["📄 Search Projects", "📊 Reporting", "🔗 Agency URL"])
    
    with t1:
        st.write("Analyze new bid opportunities.")
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="up1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with t2:
        st.write("Extract SLA and reporting triggers from existing contracts/SOWs.")
        up_c = st.file_uploader("Upload SOW PDF", type="pdf", key="up2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with t3:
        url_in = st.text_input("Agency Portal URL:")
        if st.button("Scan Portal"):
            st.info("Portal scanning requested...")
