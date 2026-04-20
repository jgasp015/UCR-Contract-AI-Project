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
    st.error("🔑 API Key missing! Please add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE SCRUBBING ENGINE ---

def deep_query(full_text, specific_prompt, is_header=False):
    """FORCES CLEAN LISTS: NO INTROS, NO GHOST NUMBERS, NO JARGON."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    system_content = """You are a Plain English Translator for regular citizens. 
    RULES:
    1. START IMMEDIATELY: Never say 'Here is the list' or 'The goals are'.
    2. NO NUMBERS: Do not use 1, 2, 3. Use only a dash (-).
    3. ONE ITEM PER LINE: Put every point on a new line.
    4. SHORT: Max 8 words per line.
    5. SIMPLE: Use words a neighbor would understand. No legal-ese."""
    
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
            # Strip labels if the AI hallucinates them
            for skip in ["Agency:", "Project:", "Status:", "Deadline:", "- "]:
                res = res.replace(skip, "")
            return res.split('\n')[0].strip()
        
        # --- SCRUBBING LOGIC ---
        lines = res.split('\n')
        clean_lines = []
        for line in lines:
            l = line.strip()
            # Skip empty lines, AI intros, and "ghost" numbers
            if not l: continue
            if any(intro in l.lower() for intro in ["here is", "the following", "goals are"]): continue
            if l[0].isdigit() and (l.endswith(".") or len(l) < 4): continue
            
            # Ensure vertical bullet format
            if not l.startswith("-"): l = f"- {l}"
            clean_lines.append(l)
            
        return "\n".join(clean_lines)
    except: return "N/A"

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # Silent Data Fetching
    if not st.session_state.agency_name:
        with st.status("Gathering details..."):
            st.session_state.agency_name = deep_query(doc, "Agency name?", is_header=True)
            st.session_state.project_title = deep_query(doc, "Project title?", is_header=True)
            raw_date = deep_query(doc, "Deadline date (MM/DD/YYYY)?", is_header=True)
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- THE CLEAN HEADER ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.subheader(st.session_state.project_title)
    st.write(f"**{st.session_state.agency_name}**")
    st.divider()

    # --- DATA TABS ---
    if not st.session_state.summary_ans:
        with st.status("Simplifying for you..."):
            st.session_state.bid_details = deep_query(doc, "List the Bid ID, Buyer, and Email.")
            st.session_state.summary_ans = deep_query(doc, "What are the 5 main goals? Simple 1-line points.")
            st.session_state.tech_ans = deep_query(doc, "What computers or software do they need?")
            st.session_state.submission_ans = deep_query(doc, "Steps to sign up. 1 short line per step.")
            st.session_state.compliance_ans = deep_query(doc, "Main 3 simple rules to follow.")
            st.session_state.award_ans = deep_query(doc, "How do they choose the winner?")
            st.rerun()

    t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    
    t_det.markdown(st.session_state.bid_details)
    t_plan.info(st.session_state.summary_ans)
    t_tech.success(st.session_state.tech_ans)
    t_apply.warning(st.session_state.submission_ans)
    t_legal.error(st.session_state.compliance_ans)
    t_award.write(st.session_state.award_ans)

else:
    tab1, tab2, tab3 = st.tabs(["📄 Search Projects", "📊 Reporting", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            reader = PdfReader(up)
            st.session_state.active_bid_text = "".join([p.extract_text() for p in reader.pages])
            st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Reporting PDF", type="pdf")
        if up_c:
            reader = PdfReader(up_c)
            st.session_state.active_bid_text = "".join([p.extract_text() for p in reader.pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with tab3:
        url_in = st.text_input("Agency Portal URL:")
        if st.button("Scan Portal"):
            st.warning("Portal scanner requires ChromeDriver in environment.")
            st.rerun()
