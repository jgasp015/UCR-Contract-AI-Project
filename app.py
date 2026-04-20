import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- 1. SESSION STATE ---
def init_state():
    keys = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'analysis_mode': "Standard",
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, is_header=False):
    """FORCES SIMPLE ENGLISH AND SHORT BULLETS ONLY."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    system_content = """You are a Plain English Translator for government documents. 
    RULES:
    1. SIMPLE WORDS: Use 5th-grade level English.
    2. ONE LINE ONLY: Each bullet point must be one short line.
    3. NO PARAGRAPHS: Never write a paragraph.
    4. NO LABELS: Do not repeat the prompt.
    5. NO LEGAL TALK: Replace 'indemnify' with 'be responsible' or 'pay for'."""
    
    if is_header:
        system_content = "Respond with ONLY the name requested. Zero extra words."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:10000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        if is_header:
            for skip in ["Agency:", "Project:", "Status:", "Deadline:", "- "]:
                res = res.replace(skip, "")
            return res.split('\n')[0]
        return res
    except: return "N/A"

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.status("Reading document..."):
            st.session_state.agency_name = deep_query(doc, "Agency name?", is_header=True)
            st.session_state.project_title = deep_query(doc, "Project title?", is_header=True)
            raw_date = deep_query(doc, "Deadline date MM/DD/YYYY?", is_header=True)
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- HEADER ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.subheader(st.session_state.project_title)
    st.write(f"**{st.session_state.agency_name}**")
    st.divider()

    # --- TABS (NOW IN SIMPLE ENGLISH) ---
    if not st.session_state.summary_ans:
        with st.status("Simplifying document..."):
            st.session_state.bid_details = deep_query(doc, "List the ID number, buyer name, and email in 1 line each.")
            st.session_state.summary_ans = deep_query(doc, "What are the 5 main things they want to do? Use 1 line per goal.")
            st.session_state.tech_ans = deep_query(doc, "What computers or software do they need? 1 line per item.")
            st.session_state.submission_ans = deep_query(doc, "How do I sign up? Give me simple steps, 1 line each.")
            st.session_state.compliance_ans = deep_query(doc, "What are the main rules I must follow? Simple words only.")
            st.session_state.award_ans = deep_query(doc, "How do they pick who wins? Simple points.")
            st.rerun()

    t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    t_det.write(st.session_state.bid_details)
    t_plan.info(st.session_state.summary_ans)
    t_tech.success(st.session_state.tech_ans)
    t_apply.warning(st.session_state.submission_ans)
    t_legal.error(st.session_state.compliance_ans)
    t_award.write(st.session_state.award_ans)

else:
    tab1, tab2, tab3 = st.tabs(["📄 Search", "📊 Reporting", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Reporting PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with tab3:
        url_in = st.text_input("Agency URL:")
        if st.button("Scan"):
            st.rerun()
