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
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE IMPROVED ANALYSIS ENGINE ---

def deep_query(full_text, specific_prompt, is_header=False):
    """
    NEW LOGIC: Analyzes the START and the END of the file to find 
    actual project goals, ignoring the middle legal 'wall of text'.
    """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Focus on the first 4 pages and the last 5 pages where the meat is
    condensed_text = full_text[:8000] + "\n[...]\n" + full_text[-8000:]
    
    system_content = """You are an expert at explaining government projects to normal people.
    RULES:
    1. IGNORE LEGAL JUNK: Skip rules about 'indemnity', 'lobbying', or 'gratuities'.
    2. FIND THE MEAT: Look for the 'Price Sheet' or 'Commodity Description' at the end of the file.
    3. MOM-TEST: Use 5-word lines. No big words. 
    4. VERTICAL: Every point must start with '-' on a new line.
    5. NO REPEATING: If you already said it, don't say it again."""
    
    if is_header:
        system_content = "Return ONLY the name. No extra words."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nDOCUMENT TEXT:\n{condensed_text}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        
        if is_header:
            return res.split('\n')[0].replace("Agency:", "").replace("Project:", "").strip()
        
        # Scrub out AI chatter and force vertical lines
        lines = [line.strip() for line in res.split('\n') if line.strip() and not any(x in line.lower() for x in ["here is", "the goals", "text:"])]
        formatted = ""
        for l in lines:
            if not l.startswith("-"): l = f"- {l}"
            formatted += f"{l}\n\n"
        return formatted
    except: return "N/A"

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.status("Finding the important parts..."):
            st.session_state.agency_name = deep_query(doc, "Which city or county is this?", is_header=True)
            st.session_state.project_title = deep_query(doc, "What is the short project name?", is_header=True)
            raw_date = deep_query(doc, "Deadline date MM/DD/YYYY?", is_header=True)
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- HEADER (STAYS AT TOP) ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.subheader(st.session_state.project_title)
    st.write(f"**{st.session_state.agency_name}**")
    st.divider()

    # --- TABS (SIMPLE LISTS) ---
    if not st.session_state.summary_ans:
        with st.status("Analyzing Project Goals..."):
            st.session_state.bid_details = deep_query(doc, "Bid ID? Person in charge? Their email?")
            st.session_state.summary_ans = deep_query(doc, "Look at the PRICE SHEET/COMMODITY section. What are the 4 main goals? Use simple words.")
            st.session_state.tech_ans = deep_query(doc, "What specific software or hardware is mentioned at the END of the file?")
            st.session_state.submission_ans = deep_query(doc, "How to apply? Simple 3 steps.")
            st.session_state.compliance_ans = deep_query(doc, "What are the 3 main rules? Use easy words like 'No paper' or 'Insurance needed'.")
            st.session_state.award_ans = deep_query(doc, "How do they choose who wins? (Example: Lowest price).")
            st.rerun()

    t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    
    t_det.markdown(st.session_state.bid_details)
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
