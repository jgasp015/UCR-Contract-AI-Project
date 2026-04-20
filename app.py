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

# --- 2. THE IMPROVED COMBINED ENGINE ---

def deep_query(full_text, specific_prompt, persona="General", is_header=False):
    """
    Analyzes the START and END of the document to find the meat.
    Switches personas based on analysis_mode.
    """
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Focus on crucial pages (first ~8k chars and last ~8k chars)
    condensed_text = full_text[:8000] + "\n[...]\n" + full_text[-8000:]
    
    if persona == "Reporting":
        system_content = """You are a Public Records Assistant specializing in service standards.
        RULES:
        1. FIND THE TRIGGERS: Look for SLA targets, 'Catastrophic Outage' definitions, and 'Stop Clock' rules.
        2. NO JARGON: Use very simple words for a regular citizen.
        3. VERTICAL: Use bullet points (-) on new lines. No paragraphs."""
    else:
        system_content = """You are a Public Records Assistant explaining projects to a neighbor.
        RULES:
        1. MOM-TEST: Use 5-word lines. Simple words only.
        2. NO LEGAL JUNK: Skip indemnity/lobbying rules.
        3. FIND THE MEAT: Look at the Price Sheet or Commodity Description at the end.
        4. START IMMEDIATELY: No intros like 'Here is the info'."""

    if is_header:
        system_content = "Return ONLY the name requested. Zero extra words. No labels."

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
            # Clean up hallucinated labels
            for skip in ["Agency:", "Project:", "Status:", "Deadline:", "- "]:
                res = res.replace(skip, "")
            return res.split('\n')[0].strip()
        
        # Scrub out AI chitchat and ghost numbers
        lines = res.split('\n')
        clean_lines = []
        for line in lines:
            l = line.strip()
            if not l or any(x in l.lower() for x in ["here is", "the following", "text:"]): continue
            if l[0].isdigit() and (l.endswith(".") or len(l) < 4): continue
            if not l.startswith("-"): l = f"- {l}"
            clean_lines.append(l)
            
        return "\n\n".join(clean_lines)
    except: return "Information not found."

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

    # --- SILENT HEADER EXTRACTION ---
    if not st.session_state.agency_name:
        with st.status("Gathering Document Context..."):
            st.session_state.agency_name = deep_query(doc, "Which city or county is this?", is_header=True)
            st.session_state.project_title = deep_query(doc, "What is the short project name?", is_header=True)
            raw_date = deep_query(doc, "Deadline date (MM/DD/YYYY)?", is_header=True)
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except: st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- NO-GAP TOP HEADER ---
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
            with st.status("📊 Checking Service Standards..."):
                prompt = """
                Extract these 4 rules from the SOW/Contract:
                1. How is 'uptime' or 'availability' measured?
                2. What happens if the service is broken for too long?
                3. What counts as a 'catastrophic' or 'major' problem?
                4. What are the rules for pausing the service clock (Stop Clock)?
                """
                st.session_state.report_ans = deep_query(doc, prompt, persona="Reporting")
                st.session_state.total_saved += 60
                st.rerun()
        
        st.info("### 📊 Contract Rules & Standards")
        st.markdown(st.session_state.report_ans)

    else:
        if not st.session_state.summary_ans:
            with st.status("Simplifying Project Details..."):
                st.session_state.bid_details = deep_query(doc, "Bid ID? Person in charge? Email?")
                st.session_state.summary_ans = deep_query(doc, "Look at the PRICE SHEET/COMMODITY section. What are the 4 main goals?")
                st.session_state.tech_ans = deep_query(doc, "What computers or software are needed?")
                st.session_state.submission_ans = deep_query(doc, "Simple steps to sign up.")
                st.session_state.compliance_ans = deep_query(doc, "Main 3 rules? (e.g. No paper, Insurance needed).")
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
    t1, t2, t3 = st.tabs(["📄 New Bid Search", "📊 Contract Rules", "🔗 Agency URL"])
    
    with t1:
        st.write("Understand new project opportunities.")
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="up1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with t2:
        st.write("Understand the rules and triggers of an existing contract.")
        up_c = st.file_uploader("Upload Contract or SOW PDF", type="pdf", key="up2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with t3:
        url_in = st.text_input("Enter Government Portal URL:")
        if st.button("Scan Portal"):
            st.info("Scanner requires local driver setup.")
