import streamlit as st
import requests
from pypdf import PdfReader
import io
import time # THE FIX: Allows us to space out the requests

# --- SILO 1: SESSION & STATE ---
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

# --- SILO 2: THE "PATIENT" AI ENGINE ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    # THE FIX: A 0.6 second pause between every single AI question
    time.sleep(0.6) 
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] if context_slice == "start" else text[:10000] + "\n[...]\n" + text[-10000:]
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        data = response.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return "⚠️ AI is thinking... please wait and it will appear."
    except:
        return "⚠️ Connection hiccup. It will retry in a second."

# --- SILO 3: UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance, Penalties & Stop-Clock Rules")
        if not st.session_state.report_ans:
            with st.spinner("Analyzing SLA Rules (Step 1 of 1)..."):
                prompt = "Explain: 1. HOW to report, 2. Uptime targets, 3. PENALTIES, 4. STOP-CLOCK conditions, 5. Monthly reports."
                st.session_state.report_ans = run_ai(doc, prompt, "Contract Compliance Expert. High Detail.")
        st.markdown(st.session_state.report_ans)
    else:
        # MOM-TEST BID VIEW
        if not st.session_state.agency_name:
            with st.status("Fetching Header Info...") as s:
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Name only.", "start")
                st.session_state.project_title = run_ai(doc, "Project Name?", "Name only.", "start")
                st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
                s.update(label="Header Ready!", state="complete")
                st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        
        if not st.session_state.summary_ans:
            with st.status("Simplifying Content (Please wait 5 seconds)...") as s:
                st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
                st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test points.")
                st.session_state.tech_ans = run_ai(doc, "Tools needed? Max 5 points.", "List items.")
                st.session_state.submission_ans = run_ai(doc, "How to apply?", "1, 2, 3.", "start")
                st.session_state.compliance_ans = run_ai(doc, "Rules/Insurance?", "Mom-test points.")
                st.session_state.award_ans = run_ai(doc, "How to win?", "Simple list.")
                s.update(label="Analysis Complete!", state="complete")
                st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].markdown(st.session_state.bid_details)
        tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans)
        tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans)
        tabs[5].write(st.session_state.award_ans)

else:
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
    with t3:
        u_in = st.text_input("Agency URL:", placeholder="Paste link here...")
        # Scraper logic remains safe
