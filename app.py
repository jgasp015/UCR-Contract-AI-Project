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
if 'agency_name' not in st.session_state: st.session_state.agency_name = None
if 'project_title' not in st.session_state: st.session_state.project_title = None

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'status_flag', 'detected_due_date']
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
    """AI Engine strictly configured for clean Markdown lists."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Government Data Extractor. TODAY IS APRIL 20, 2026.
                STRICT RULES:
                1. NO INTROS: Do not say 'Here is the data' or repeat titles.
                2. FORMATTING: Use Markdown bullet points (-). 
                3. NO GREETINGS: Start directly with data.
                4. CONCISE: Provide facts only."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Data missing."

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
            st.session_state.agency_name = deep_query(doc, "Agency name? (e.g. Los Angeles County). ONLY the name.")
            st.session_state.project_title = deep_query(doc, "Short project title? ONLY the name.")
            raw_date = deep_query(doc, "Deadline? (MM/DD/YYYY). ONLY the date.")
            st.session_state.detected_due_date = raw_date
            
            # Status Logic
            today = datetime(2026, 4, 20)
            status_ai = deep_query(doc, "Is this bid OPEN, CLOSED, ACTIVE, or AWARDED? Give 1 word.")
            st.session_state.status_flag = status_ai.upper()
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                if clean_date < today and "AWARDED" not in st.session_state.status_flag:
                    st.session_state.status_flag = "CLOSED"
            except: pass

    # --- THE HEADER: STATUS > DATE > AGENCY > PROJECT TITLE ---
    if "OPEN" in st.session_state.status_flag:
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    elif "AWARDED" in st.session_state.status_flag:
        st.info(f"● AWARDED | Project Completed")
    elif "ACTIVE" in st.session_state.status_flag:
        st.warning(f"● ACTIVE | Ongoing Project")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider() # Everything below here is in tabs

    # --- TABS ---
    if not st.session_state.summary_ans:
        with st.status("🚀 Organizing Data..."):
            st.session_state.bid_details = deep_query(doc, "List Solicitation Number, Buyer Name, Email, and Phone as bullet points.")
            st.session_state.summary_ans = deep_query(doc, "Bulleted list of project goals.")
            st.session_state.tech_ans = deep_query(doc, "Bulleted list of software/hardware specs. If none, say General IT.")
            st.session_state.submission_ans = deep_query(doc, "Bulleted list of application steps.")
            st.session_state.compliance_ans = deep_query(doc, "Bulleted list of insurance/legal rules.")
            st.session_state.award_ans = deep_query(doc, "Winner selection facts.")
            st.rerun()

    tabs = st.tabs(["📋 Bid Details", "📖 Project Plan", "🛠️ Technology", "📝 Application Process", "⚖️ Legal Rules", "💰 Winner Selection"])
    tabs[0].write(st.session_state.bid_details)
    tabs[1].info(st.session_state.summary_ans)
    tabs[2].success(st.session_state.tech_ans)
    tabs[3].warning(st.session_state.submission_ans)
    tabs[4].error(st.session_state.compliance_ans)
    tabs[5].write(st.session_state.award_ans)

# --- VIEW 2 & 3 (Rest of code remains the same) ---
elif st.session_state.all_bids:
    if st.button("⬅️ Back"):
        st.session_state.all_bids = []
        st.rerun()
    for idx, bid in enumerate(st.session_state.all_bids):
        if st.button(bid['name'], key=idx):
            st.session_state.active_bid_text = bid['full_text']
            st.session_state.active_bid_name = bid['name']
            st.rerun()
else:
    t1, t2 = st.tabs(["📄 Search Projects", "📊 Reporting Standards"])
    with t1:
        up_bid = st.file_uploader("Upload PDF", type="pdf")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.active_bid_name = up_bid.name
            st.rerun()
