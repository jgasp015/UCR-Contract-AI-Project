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

# --- 2. THE PRECISION ENGINE ---

def deep_query(full_text, specific_prompt, persona="General", is_header=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Targeting Logic: Bids look at end, Reporting looks at whole second half
    if is_header:
        context_text = full_text[:8000]
    elif persona == "Reporting":
        mid = len(full_text) // 2
        context_text = full_text[mid:] 
    elif any(x in specific_prompt.lower() for x in ["tech", "goal", "award", "software"]):
        context_text = full_text[-15000:] 
    elif any(x in specific_prompt.lower() for x in ["rule", "legal", "insurance"]):
        context_text = full_text[2000:20000] 
    else:
        context_text = full_text[:8000] + "\n[...]\n" + full_text[-10000:]

    # Persona Selection
    if persona == "Reporting":
        system_content = """You are a Public Records Assistant explaining active contract rules to a mother.
        RULES:
        1. NO JARGON: Use simple words like 'Service Promise' or 'Setup Time'.
        2. FIND EVERYTHING: Availability, CAT 2 & 3 Outages, and Setup Times.
        3. STOP CLOCKS: Explain when they can 'pause the timer'.
        4. VERTICAL: Dash (-) on new lines. No paragraphs."""
    else:
        system_content = """You are a Public Records Assistant. 
        RULES:
        1. MOM-TEST: 5-word lines. Simple words only.
        2. NO REPEATING: Never say the same thing twice.
        3. NO FILLER: No intros. Start with '-'.
        4. ACCURACY: Look for 'Price Sheet' for software names."""

    if is_header:
        system_content = "Return ONLY the name requested. No labels."

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
        
        # Scrubbing logic for vertical lists
        lines = res.split('\n')
        clean_lines = []
        seen = set()
        for line in lines:
            l = line.strip().lower()
            if not l or any(x in l for x in ["hello", "neighbor", "here is", "following"]): continue
            if l in seen: continue 
            display_line = line.strip()
            if not display_line.startswith("-"): display_line = f"- {display_line}"
            clean_lines.append(display_line)
            seen.add(l)
            
        return "\n\n".join(clean_lines[:10])
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

    # --- WORKFLOW SWITCHER ---
    
    # MODE A: REPORTING (NO HEADER)
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Reading Service Promises..."):
                prompt = """
                Explain these service promises in very simple words for a mother:
                1. UPTIME: What % must the service stay working?
                2. SETUP TIME: How many days to install things?
                3. MAJOR PROBLEMS: What counts as a big crash?
                4. TOO LONG: How many hours is considered too slow to fix?
                5. PAUSING THE TIMER: List reasons they can stop the 'repair clock'.
                """
                st.session_state.report_ans = deep_query(doc, prompt, persona="Reporting")
                st.session_state.total_saved += 60
                st.rerun()
        st.info("### 📊 Active Contract: Service Promises & Rules")
        st.markdown(st.session_state.report_ans)

    # MODE B: BID DOCUMENT (WITH HEADER)
    else:
        if not st.session_state.agency_name:
            with st.status("Analyzing Bid..."):
                st.session_state.agency_name = deep_query(doc, "Agency issuing this?", is_header=True)
                st.session_state.project_title = deep_query(doc, "Project title?", is_header=True)
                raw_date = deep_query(doc, "Deadline MM/DD/YYYY?", is_header=True)
                st.session_state.detected_due_date = raw_date
                try:
                    clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                    st.session_state.status_flag = "CLOSED" if clean_date < datetime(2026, 4, 20) else "OPEN"
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
            with st.status("Gathering Specific Facts..."):
                st.session_state.bid_details = deep_query(doc, "Solicitation Number and Buyer Email only.")
                st.session_state.summary_ans = deep_query(doc, "What are the specific project goals?")
                st.session_state.tech_ans = deep_query(doc, "List specific software name and gear needed.")
                st.session_state.submission_ans = deep_query(doc, "3 simple steps to apply.")
                st.session_state.compliance_ans = deep_query(doc, "List specific insurance limits and conduct rules.")
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

else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with t3:
        url_in = st.text_input("Agency URL:")
        if st.button("Scan"): st.info("Requires local driver.")
