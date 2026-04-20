import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime

# --- 1. SESSION STATE INITIALIZATION ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_name' not in st.session_state: st.session_state.active_bid_name = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'agency_name' not in st.session_state: st.session_state.agency_name = None
if 'project_title' not in st.session_state: st.session_state.project_title = None

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Government Data Extractor. TODAY IS APRIL 20, 2026.
                RULES: 1. No explanations. 2. If missing, say 'Not Specified'. 3. Be concise. 4. No greetings."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Unknown"

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    if st.button("🏠 Return Home"):
        for k in ['all_bids', 'active_bid_text', 'active_bid_name', 'agency_name', 'project_title'] + keys:
            st.session_state[k] = [] if k == 'all_bids' else None
        st.rerun()

# --- VIEW 1: ANALYSIS VIEW ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to List"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.spinner("Processing..."):
            st.session_state.agency_name = deep_query(doc, "Agency name? ONLY the name.")
            st.session_state.project_title = deep_query(doc, "Project title? ONLY the name.")
            raw_date = deep_query(doc, "Deadline? (MM/DD/YYYY). ONLY the date.")
            st.session_state.detected_due_date = raw_date
            
            # --- STRICT DATE LOGIC ---
            today = datetime(2026, 4, 20)
            try:
                # Try to parse the date found by AI
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                if clean_date < today:
                    st.session_state.status_flag = "CLOSED"
                else:
                    st.session_state.status_flag = "OPEN"
            except:
                # If date format is weird, fallback to AI judgment
                status_check = deep_query(doc, "Is this bid OPEN or CLOSED? (Today is April 20, 2026). Give 1 word.")
                st.session_state.status_flag = "CLOSED" if "CLOSED" in status_check.upper() else "OPEN"

    # --- THE CLEAN HEADER ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider()

    # --- TABS ---
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            st.session_state.report_ans = deep_query(doc, "Summary of standards: 1. Uptime 2. Fix times 3. Penalties. No intros.")
            st.rerun()
        st.markdown(st.session_state.report_ans)
    else:
        if not st.session_state.summary_ans:
            st.session_state.summary_ans = deep_query(doc, "Project goal. No intros.")
            st.session_state.tech_ans = deep_query(doc, "Required gear. No intros.")
            st.session_state.submission_ans = deep_query(doc, "Steps to apply. No intros.")
            st.session_state.compliance_ans = deep_query(doc, "Legal rules. No intros.")
            st.session_state.award_ans = deep_query(doc, "Winner selection facts. No intros.")
            st.rerun()

        tabs = st.tabs(["📖 Project Plan", "🛠️ Technology", "📝 Application Process", "⚖️ Legal Rules", "💰 Winner Selection"])
        tabs[0].info(st.session_state.summary_ans)
        tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans)
        tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS (REDACTED FOR BREVITY) ---
elif st.session_state.all_bids:
    if st.button("⬅️ Back"):
        st.session_state.all_bids = []
        st.rerun()
    for idx, bid in enumerate(st.session_state.all_bids):
        if st.button(bid['name'], key=idx):
            st.session_state.active_bid_text = bid['full_text']
            st.session_state.active_bid_name = bid['name']
            st.rerun()

# --- VIEW 3: INITIAL SEARCH ---
else:
    t1, t2 = st.tabs(["📄 New Project Search", "📊 Performance Standards"])
    with t1:
        up_bid = st.file_uploader("Upload Bid PDF", type="pdf", key="up_bid")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.session_state.analysis_mode = "Standard"
            st.rerun()
    with t2:
        up_rep = st.file_uploader("Upload Contract PDF", type="pdf", key="up_rep")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.active_bid_name = up_rep.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
