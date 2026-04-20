import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime

# --- 1. SESSION STATE INITIALIZATION ---
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

def clear_document_data():
    for key in ['agency_name', 'project_title', 'status_flag', 'detected_due_date', 
                'summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 
                'award_ans', 'bid_details', 'report_ans']:
        st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 GROQ_API_KEY missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE DUAL INDEPENDENT ENGINES ---

def reporting_query(full_text, specific_prompt):
    """STRICT ENGINE: FORCES EXTRACTION OF REAL NUMBERS FROM TABLES."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # SLAs are almost always in the last 30% of CALNET/Gov docs
    start_point = int(len(full_text) * 0.6)
    context_text = full_text[start_point:] 

    system_content = """You are a Public Records Assistant. 
    Your goal is to find the EXACT numbers in the Service Level Agreement (SLA) tables.
    RULES:
    1. NO PLACEHOLDERS: Do not guess. Do not say '1 hour' unless you see '1 hour' in the text.
    2. FIND THE PREMIER LEVEL: Most of these have Basic, Standard, and Premier. Always report the Premier (best) level.
    3. NO INTROS: Start immediately with facts.
    4. REPORTING: Look for 'Methods of Outage Reporting'. Find the phone number or tool name.
    5. VERTICAL: Use dash (-) and simple words for a mother."""

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{context_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        return format_vertical_list(res)
    except: return "N/A"

def bid_query(full_text, specific_prompt, is_header=False):
    """PRECISION ENGINE FOR BID DOCUMENTS."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if is_header:
        context_text = full_text[:8000]
    elif any(x in specific_prompt.lower() for x in ["tech", "goal", "award", "software"]):
        context_text = full_text[-15000:] 
    else:
        context_text = full_text[:8000] + "\n[...]\n" + full_text[-10000:]

    system_content = "You are a Public Records Assistant. RULES: 1. MOM-TEST. 2. NO REPEATING. 3. NO FILLER."
    if is_header: system_content = "Return ONLY the name requested. No labels."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{context_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        if is_header:
            for skip in ["Agency:", "Project:", "Status:", "Deadline:", "- "]:
                res = res.replace(skip, "")
            return res.split('\n')[0].strip()
        return format_vertical_list(res)
    except: return "N/A"

def format_vertical_list(text):
    lines = text.split('\n')
    clean_lines = []
    seen = set()
    for line in lines:
        l = line.strip().lower()
        if not l or any(x in l for x in ["hello", "neighbor", "here is", "following", "requested", "instruction"]): continue
        if l in seen: continue 
        display_line = line.strip()
        if not display_line.startswith("-"): display_line = f"- {display_line}"
        clean_lines.append(display_line)
        seen.add(l)
    return "\n\n".join(clean_lines[:15])

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_document_data()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Scanning for specific Service Promises..."):
                prompt = """
                Look at the SLA tables and extract the EXACT requirements:
                1. UPTIME: What is the % required for the 'Premier' level?
                2. SETUP: Look for 'Provisioning'. How many days to install?
                3. MAJOR PROBLEMS: Look for 'Catastrophic Outage 2' and '3'. How many minutes/hours to fix?
                4. TOO SLOW: Look for 'Excessive Outage'. What is the time limit?
                5. PAUSING: Find 'Stop Clock Conditions'. List the top 3 simple reasons.
                6. REPORTING: Look for 'Methods of Outage Reporting'. How does a person report a problem?
                """
                st.session_state.report_ans = reporting_query(doc, prompt)
                st.session_state.total_saved += 60
                st.rerun()
        st.info("### 📊 Active Contract: Service Promises & Rules")
        st.markdown(st.session_state.report_ans)

    else:
        # Standard Bid Mode Logic (preserved)
        if not st.session_state.agency_name:
            with st.status("Reading Bid..."):
                st.session_state.agency_name = bid_query(doc, "Agency issuing this?", is_header=True)
                st.session_state.project_title = bid_query(doc, "Project title?", is_header=True)
                st.session_state.detected_due_date = bid_query(doc, "Deadline date?", is_header=True)
                st.session_state.status_flag = "OPEN"
                st.rerun()

        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        st.divider()

        if not st.session_state.summary_ans:
            with st.status("Analyzing Bid Details..."):
                st.session_state.bid_details = bid_query(doc, "Solicitation ID and Buyer Email only.")
                st.session_state.summary_ans = bid_query(doc, "What are the specific project goals?")
                st.session_state.tech_ans = bid_query(doc, "List specific software and gear needed.")
                st.session_state.submission_ans = bid_query(doc, "3 simple steps to apply.")
                st.session_state.compliance_ans = bid_query(doc, "Insurance and conduct rules.")
                st.session_state.award_ans = bid_query(doc, "How they pick the winner?")
                st.session_state.total_saved += 120
                st.rerun()

        t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t_det.markdown(st.session_state.bid_details)
        t_plan.info(st.session_state.summary_ans)
        t_tech.success(st.session_state.tech_ans)
        t_apply.warning(st.session_state.submission_ans)
        t_legal.error(st.session_state.compliance_ans)
        t_award.write(st.session_state.award_ans)

else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            clear_document_data()
            st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            clear_document_data()
            st.rerun()
    with t3:
        url_in = st.text_input("Agency URL:")
        if st.button("Scan"): st.info("Requires driver.")
