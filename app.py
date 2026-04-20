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
    """STRICT ANALYST ENGINE: EXCLUSIVELY FOR SOW/SLA COMPLIANCE."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Target the Service Level Agreement (SLA) section (usually starts 60% through)
    start_point = int(len(full_text) * 0.6)
    context_text = full_text[start_point:] 

    system_content = """You are a Contract Compliance Assistant for new contractors.
    Your job is to extract CRITICAL reporting rules from the document text provided.
    RULES:
    1. EXTRACT REAL NUMBERS: You must find the Premier Level % and the fix times in minutes/hours.
    2. HOW TO REPORT: Find the section 'Methods of Outage Reporting'. State exactly how they report (Help Desk, Phone, Tool).
    3. STOP CLOCKS: Find the 'Stop Clock Conditions'. List the specific reasons they can pause the timer.
    4. NO GREETINGS: Start immediately with factual bullet points.
    5. LANGUAGE: Use simple, clear English for a non-expert."""

    payload = {
        "model": "llama-3.1-70b-versatile", # Switched to 70B for higher accuracy in data extraction
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nDOCUMENT TEXT:\n{context_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=45)
        res = response.json()['choices'][0]['message']['content'].strip()
        return format_vertical_list(res)
    except: return "Unable to parse contract data. Please ensure the PDF contains SLA tables."

def bid_query(full_text, specific_prompt, is_header=False):
    """PRECISION ENGINE FOR BID DOCUMENTS."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    if is_header:
        context_text = full_text[:8000]
    elif any(x in specific_prompt.lower() for x in ["tech", "goal", "award", "software"]):
        context_text = full_text[-15000:] 
    else:
        context_text = full_text[:8000] + "\n[...]\n" + full_text[-10000:]

    system_content = "You are a Public Records Assistant. RULES: 1. Simple English. 2. No repeating. 3. No intros."
    if is_header: system_content = "Return ONLY the name. No labels."

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
        if not l or any(x in l for x in ["hello", "neighbor", "here is", "following", "requested"]): continue
        if l in seen: continue 
        display_line = line.strip()
        if not display_line.startswith("-"): display_line = f"- {display_line}"
        clean_lines.append(display_line)
        seen.add(l)
    return "\n\n".join(clean_lines[:15])

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.metric("Est. Time Saved", f"{st.session_state.total_saved}m")
    if st.button("🏠 Home"):
        st.session_state.active_bid_text = None
        clear_document_data()
        st.rerun()

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_document_data()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Scanning SLA Tables & Reporting Rules..."):
                prompt = """
                Extract the specific Performance Standards from this contract:
                1. UPTIME: What is the exact Premier level percentage (e.g., 99.9%)?
                2. FIX TIMES: How many minutes/hours for 'Catastrophic Outage 2', '3', and 'Excessive Outage'?
                3. SETUP: How many days for 'Provisioning' or 'Installation'?
                4. STOP CLOCK: List the specific reasons allowed to pause the timer (e.g. building access, power issues).
                5. HOW TO REPORT: State the specific method a customer uses to report an issue (e.g., Help Desk name, Tool name).
                """
                st.session_state.report_ans = reporting_query(doc, prompt)
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Active Contract: Service Performance & Reporting Guide")
        st.markdown(st.session_state.report_ans)

    else:
        # Standard Bid Mode (Unchanged)
        if not st.session_state.agency_name:
            with st.status("Reading Bid Header..."):
                st.session_state.agency_name = bid_query(doc, "Agency issuing this?", is_header=True)
                st.session_state.project_title = bid_query(doc, "Project title?", is_header=True)
                raw_date = bid_query(doc, "Deadline date?", is_header=True)
                st.session_state.detected_due_date = raw_date
                st.rerun()

        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        st.divider()

        if not st.session_state.summary_ans:
            with st.status("Analyzing Project Details..."):
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
        up_c = st.file_uploader("Upload SOW or Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            clear_document_data()
            st.rerun()
    with t3:
        url_in = st.text_input("Agency URL:")
        if st.button("Scan"): st.info("Requires local driver.")
