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

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 GROQ_API_KEY missing in Streamlit Secrets!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE DUAL-MODE ENGINE ---

def deep_query(full_text, specific_prompt, persona="General", is_header=False):
    """
    Targets specific sections of the text to prevent 'not reading' errors.
    """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Segmenting text: Headers use start, Reporting uses end/middle (where SLAs live), Bids use end (Price sheets)
    if is_header:
        context_text = full_text[:10000]
    elif persona == "Reporting":
        # SLAs are usually in the second half of these documents
        mid = len(full_text) // 2
        context_text = full_text[mid:mid+20000] 
    else:
        context_text = full_text[:8000] + "\n[...]\n" + full_text[-10000:]

    if persona == "Reporting":
        system_content = """You are a Public Records Assistant. 
        Your goal is to explain Uptime, Availability, and Provisioning rules.
        RULES:
        1. NO JARGON: Use simple words.
        2. BE SPECIFIC: If it says '99.9% uptime', include that number.
        3. VERTICAL: Bullet points only. No paragraphs."""
    else:
        system_content = """You are a Public Records Assistant explaining projects to a neighbor.
        RULES:
        1. MOM-TEST: Simple words.
        2. FIND THE MEAT: Look for actual goals and price items.
        3. NO CHITCHAT: Start immediately with facts."""

    if is_header:
        system_content = "Return ONLY the name requested. Zero extra words. No labels."

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"{specific_prompt}\n\nDOCUMENT TEXT:\n{context_text}"}
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
        
        # Cleanup
        lines = [l.strip() for l in res.split('\n') if l.strip() and "here is" not in l.lower()]
        formatted = ""
        for l in lines:
            if not l.startswith("-"): l = f"- {l}"
            formatted += f"{l}\n\n"
        return formatted
    except: return "Document analysis timed out. Please try a smaller file or a specific page."

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.metric("Est. Time Saved", f"{st.session_state.total_saved}m")
    if st.button("🏠 Home / New Search"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # Silent Header
    if not st.session_state.agency_name:
        with st.status("Reading Header..."):
            st.session_state.agency_name = deep_query(doc, "Which city/county/state agency issued this?", is_header=True)
            st.session_state.project_title = deep_query(doc, "Short project title?", is_header=True)
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
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Extracting Availability & Provisioning Rules..."):
                prompt = """
                Find the Service Standards (SLA) in this contract:
                1. AVAILABILITY: What is the % uptime required? How is 'Unavailable Time' measured?
                2. PROVISIONING: How many days do they have to install new service?
                3. OUTAGES: What defines a 'Catastrophic' vs 'Excessive' outage?
                4. STOP CLOCK: When is the company allowed to stop the timer on a repair?
                """
                st.session_state.report_ans = deep_query(doc, prompt, persona="Reporting")
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Contract Performance Standards")
        st.markdown(st.session_state.report_ans)

    else:
        if not st.session_state.summary_ans:
            with st.status("Simplifying Project Goals..."):
                st.session_state.bid_details = deep_query(doc, "Bid ID? Person in charge? Email?")
                st.session_state.summary_ans = deep_query(doc, "What are the 4 main goals of this project?")
                st.session_state.tech_ans = deep_query(doc, "What software/hardware/IT gear is needed?")
                st.session_state.submission_ans = deep_query(doc, "Simple steps to sign up.")
                st.session_state.compliance_ans = deep_query(doc, "Main rules? (e.g. Insurance, No Paper Bids).")
                st.session_state.award_ans = deep_query(doc, "How do they choose the winner?")
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
    # RENAMED TO BID DOCUMENT
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        st.write("Understand a new bidding opportunity.")
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="up1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with t2:
        st.write("Check the rules/SLA for an existing contract or SOW.")
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="up2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with t3:
        url_in = st.text_input("Enter Agency Portal URL:")
        if st.button("Scan Portal"):
            st.info("Portal scanning requested...")
