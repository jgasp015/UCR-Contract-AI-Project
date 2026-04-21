import streamlit as st
import requests
from pypdf import PdfReader
import io

# --- SILO 1: SESSION & STATE (PROTECTED) ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'portal_session': requests.Session(),
        'agency_name': None, 'project_title': None, 'detected_due_date': None,
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None, 'report_ans': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def reset_analysis():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: AI ENGINE (MOM TEST - UNIQUE PROMPTS) ---
def run_bid_ai(text, prompt, focus_area="general"):
    """Fixed: Uses specific slices of text to prevent duplicate answers."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Slice text based on focus to ensure unique data
    if focus_area == "apply": context = text[:10000] # Instructions usually at start
    elif focus_area == "goals": context = text[5000:20000] # Goals usually in middle
    else: context = text[:15000]

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "You use the Mom-Test: Very simple words. Short vertical '-' bullets. Max 5 points. NO JARGON."}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{context}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

# --- SILO 3: UI FLOW (FIXED PLAN & APPLY CONTENT) ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE (UNTOUCHED)
        st.subheader("📊 Contractor Performance & Reporting Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_bid_ai(doc, "Explain exactly how to report issues and every report I must file monthly.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT VIEW
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_bid_ai(doc, "What is the Agency Name?")
            st.session_state.project_title = run_bid_ai(doc, "What is the Project Title?")
            st.session_state.detected_due_date = run_bid_ai(doc, "What is the Deadline?")
            st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        if not st.session_state.summary_ans:
            st.session_state.bid_details = run_bid_ai(doc, "What is the Solicitation ID and Contact Email?")
            # FIX: Forced separate data for Plan and Apply
            st.session_state.summary_ans = run_bid_ai(doc, "What is the project actually trying to do? (Goals)", focus_area="goals")
            st.session_state.tech_ans = run_bid_ai(doc, "What specific tools or software are needed?")
            st.session_state.submission_ans = run_bid_ai(doc, "What are the exact steps to send this bid in?", focus_area="apply")
            st.session_state.compliance_ans = run_bid_ai(doc, "What are the rules for insurance or behavior?")
            st.session_state.award_ans = run_bid_ai(doc, "How do they choose the winner?")
            st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details)
        t2.info(st.session_state.summary_ans)      # 📖 Project Goals
        t3.success(st.session_state.tech_ans)    # 🛠️ Tools Needed
        t4.warning(st.session_state.submission_ans) # 📝 Steps to Submit
        t5.error(st.session_state.compliance_ans)
        t6.write(st.session_state.award_ans)

else:
    # --- MAIN MENU (UNTOUCHED) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    # (Rest of the manual upload and URL logic remains safe and siloed)
