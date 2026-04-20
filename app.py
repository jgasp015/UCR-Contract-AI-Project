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
    st.error("🔑 GROQ_API_KEY missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE DUAL-MODE ENGINE ---

def deep_query(full_text, specific_prompt, persona="General", is_header=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Segmenting text to keep AI focused and prevent hallucinations
    if is_header:
        context_text = full_text[:10000]
    elif "rules" in specific_prompt.lower() or "legal" in specific_prompt.lower():
        context_text = full_text[5000:25000] 
    else:
        context_text = full_text[:8000] + "\n[...]\n" + full_text[-12000:]

    if persona == "Reporting":
        system_content = """You are a Public Records Assistant. 
        RULES: Simple words only. Vertical bullet points. No paragraphs."""
    else:
        system_content = """You are a Public Records Assistant.
        RULES:
        1. MOM-TEST: Use 5-word lines. Simple words only. 
        2. NO DUPLICATES: Never mention the deadline or agency name.
        3. NO CHITCHAT: No intros. Start with '-'.
        4. ULTRA-SHORT: If asked for Details, give only the ID and Name."""

    if is_header:
        system_content = "Return ONLY the name requested. Zero extra words. No labels."

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
        
        # Scrub out helper phrases and empty list artifacts
        lines = [l.strip() for l in res.split('\n') if l.strip() and not any(x in l.lower() for x in ["hello", "neighbor", "here is", "steps:"])]
        formatted = ""
        for l in lines:
            if not l.startswith("-"): l = f"- {l}"
            formatted += f"{l}\n\n"
        return formatted
    except: return "N/A"

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

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Checking Standards..."):
                prompt = "Find Service Rules: Availability/Uptime, Provisioning days, and Outage definitions."
                st.session_state.report_ans = deep_query(doc, prompt, persona="Reporting")
                st.session_state.total_saved += 60
                st.rerun()
        st.info("### 📊 Active Contract: Performance Standards")
        st.markdown(st.session_state.report_ans)

    else:
        # --- BID MODE ---
        if not st.session_state.agency_name:
            with st.status("Reading Header..."):
                st.session_state.agency_name = deep_query(doc, "Agency issuing this?", is_header=True)
                st.session_state.project_title = deep_query(doc, "Project title?", is_header=True)
                raw_date = deep_query(doc, "Deadline MM/DD/YYYY?", is_header=True)
                st.session_state.detected_due_date = raw_date
                today = datetime(2026, 4, 20)
                try:
                    clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                    st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
                except: st.session_state.status_flag = "OPEN"
                st.rerun()

        if st.session_state.status_flag == "OPEN":
            st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        else:
            st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
        
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        st.divider()

        if not st.session_state.summary_ans:
            with st.status("Simplifying document..."):
                # SHORTENED DETAILS PROMPT
                st.session_state.bid_details = deep_query(doc, "List ONLY the Solicitation Number and Buyer Email. 2 lines max.")
                st.session_state.summary_ans = deep_query(doc, "What are the 4 main goals?")
                st.session_state.tech_ans = deep_query(doc, "Hardware/Software required.")
                st.session_state.submission_ans = deep_query(doc, "Steps to sign up (VSS/WebVen).")
                st.session_state.compliance_ans = deep_query(doc, "Insurance limits and conduct rules.")
                st.session_state.award_ans = deep_query(doc, "How they pick the winner?")
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
    # HOME SCREEN - SEARCH REMOVED
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        st.write("Analyze new project opportunities.")
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
    with t2:
        st.write("Check rules for an active contract/SOW.")
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with t3:
        url_in = st.text_input("Agency URL:")
        if st.button("Scan"): st.info("Scanner requires driver.")
