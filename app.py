import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (RESTORED & LOCKED) ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 # Kept from your screen

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'agency_name', 'project_title', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS (OPTIMIZED FOR MOM-TEST) ---

def deep_query(full_text, specific_prompt, persona="Mom-Test"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # We take a larger slice of the text (20,000 characters) to ensure it reads the whole doc
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": f"You are a helpful assistant. Use the '{persona}': explain things simply with zero jargon. If data is missing, say 'Not found'. NO INTROS."
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:20000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Connection error. Click tab again."

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Return Home"):
        for k in st.session_state.keys():
            if k != 'total_saved': st.session_state[k] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # STEP 1: IDENTIFY (HEADER)
    if not st.session_state.agency_name:
        with st.status("🏗️ Reading Document..."):
            st.session_state.agency_name = deep_query(doc, "Agency Name?")
            st.session_state.project_title = deep_query(doc, "Project Title?")
            st.session_state.detected_due_date = deep_query(doc, "Deadline date?")
            st.session_state.status_flag = deep_query(doc, "Is this OPEN, CLOSED, or AWARDED?").upper()
            st.rerun()

    # HEADER DISPLAY
    status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"
    if "OPEN" in status: st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else: st.error(f"● {status} | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider()

    # STEP 2: TABS (THE FIX FOR EMPTY TABS)
    tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Winner"])
    
    with tabs[0]: # Plan
        if not st.session_state.summary_ans:
            st.session_state.summary_ans = deep_query(doc, "In 3 bullet points, what is the simple goal of this project?")
        st.info(st.session_state.summary_ans)
        
    with tabs[1]: # Tech
        if not st.session_state.tech_ans:
            st.session_state.tech_ans = deep_query(doc, "What computers, software, or tools are needed?")
        st.success(st.session_state.tech_ans)

    with tabs[2]: # Apply
        if not st.session_state.submission_ans:
            st.session_state.submission_ans = deep_query(doc, "What are the 3 easy steps to apply?")
        st.warning(st.session_state.submission_ans)

    with tabs[3]: # Rules (The one that was failing)
        if not st.session_state.compliance_ans:
            # We specifically ask for insurance/legal rules here
            st.session_state.compliance_ans = deep_query(doc, "What are the big rules or insurance requirements? Use very simple words.")
        st.error(st.session_state.compliance_ans)

    with tabs[4]: # Winner
        if not st.session_state.award_ans:
            st.session_state.award_ans = deep_query(doc, "How do they choose who wins? Is it the lowest price or best idea?")
        st.write(st.session_state.award_ans)

else:
    # MAIN MENU
    t1, t2 = st.tabs(["📄 Upload Bid", "📊 Upload Contract"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.rerun()
