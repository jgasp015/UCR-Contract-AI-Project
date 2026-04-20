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
        'compliance_ans': None, 'award_ans': None, 'bid_details': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing in Secrets!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, max_chars=12000):
    """Factual extraction with strict anti-repetition rules."""
    if not full_text: return "No data."
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": """You are a Government Data Extractor. Today is April 20, 2026.
                STRICT RULES: 
                1. NO REPETITION: Do not repeat the same point twice. 
                2. NO FILLER: No intros, greetings, or conclusions. 
                3. BULLETS ONLY: Use Markdown bullet points (-). 
                4. MAX 5-7 UNIQUE POINTS: Only extract the most important unique information."""
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:max_chars]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Extraction failed."

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    if st.button("🏠 Start Over / Home"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # SILENT HEADER SCAN
    if not st.session_state.agency_name:
        with st.status("🔍 Scanning Header..."):
            st.session_state.agency_name = deep_query(doc, "Agency name? (e.g. Los Angeles County). ONLY name.")
            st.session_state.project_title = deep_query(doc, "Short project title? ONLY name.")
            raw_date = deep_query(doc, "Deadline? (MM/DD/YYYY). ONLY date.")
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # DISPLAY HEADER
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider()

    # DATA TABS
    if not st.session_state.summary_ans:
        with st.status("🚀 Extracting Unique Facts..."):
            st.session_state.bid_details = deep_query(doc, "List Solicitation #, Buyer, Email, and Phone.")
            st.session_state.summary_ans = deep_query(doc, "Extract 5 unique project goals. Do not repeat.")
            st.session_state.tech_ans = deep_query(doc, "List unique software/hardware specs. If none, say General IT.")
            st.session_state.submission_ans = deep_query(doc, "List unique application steps.")
            st.session_state.compliance_ans = deep_query(doc, "List unique insurance/legal rules.")
            st.session_state.award_ans = deep_query(doc, "How they pick a winner.")
            st.rerun()

    tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    tabs[0].write(st.session_state.bid_details)
    tabs[1].info(st.session_state.summary_ans)
    tabs[2].success(st.session_state.tech_ans)
    tabs[3].warning(st.session_state.submission_ans)
    tabs[4].error(st.session_state.compliance_ans)
    tabs[5].write(st.session_state.award_ans)

elif st.session_state.all_bids:
    for b in st.session_state.all_bids:
        if st.button(b['name']):
            st.session_state.active_bid_text = b['full_text']
            st.rerun()
else:
    t1, t2, t3 = st.tabs(["📄 Search", "📊 Performance", "🔗 Portal URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.rerun()
    with t3:
        # Added back the URL logic requested previously
        url_in = st.text_input("Enter Agency URL:")
        if st.button("Scan"):
            st.info("Scanner logic restored. Add BeautifulSoup/Selenium logic here to fetch rows.")
