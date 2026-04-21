import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE (STRICTLY ISOLATED) ---
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

# SAFE KEY LOADING: Pulls from Streamlit Dashboard Secrets
if "GROQ_API_KEY" not in st.secrets:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: AI ENGINES (MOM-TEST & COMPLIANCE LOGIC) ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    ctx = text[:15000] if context_slice == "start" else text[:10000] + "\n[...]\n" + text[-10000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ Service busy. Please try again."

# --- SILO 3: THE CLEAN PORTAL SCANNER ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        it_k = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "MODEM", "SECURITY", "HARDWARE"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in it_k):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    hits.append({
                        "id": cols[0].get_text(strip=True), 
                        "desc": cols[1].get_text(strip=True).split("Commodity:")[0].strip()
                    })
        return hits
    except: return []

# --- SILO 4: UI FLOW ---
st.title("🏛️ Reporting Tool") # Updated name per your request

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.get('total_saved', 0)} mins")
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance, Penalties & Stop-Clock Rules")
        if not st.session_state.report_ans:
            with st.status("🔍 Extracting SLAs..."):
                prompt = "Explain: 1. HOW to report, 2. Uptime targets, 3. PENALTIES, 4. STOP-CLOCK conditions, 5. Monthly reports."
                st.session_state.report_ans = run_ai(doc, prompt, "Contract Compliance Expert. High Detail.")
        st.markdown(st.session_state.report_ans)
    else:
        if not st.session_state.agency_name:
            with st.status("🏗️ Building Header..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Name only.", "start")
                st.session_state.project_title = run_ai(doc, "Project Name?", "Name only.", "start")
                st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
            st.rerun()
        
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        
        if not st.session_state.summary_ans:
            with st.status("🚀 Deep Scanning..."):
                st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
                st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test points.")
                st.session_state.tech_ans = run_ai(doc, "Tools needed? Max 5 points.", "List items.")
                st.session_state.submission_ans = run_ai(doc, "How to apply?", "1, 2, 3.", "start")
                st.session_state.compliance_ans = run_ai(doc, "Simple rules/Insurance?", "Mom-test points.")
                st.session_state.award_ans = run_ai(doc, "How to win?", "Simple list.")
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].markdown(st.session_state.bid_details); tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans); tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans); tabs[5].write(st.session_state.award_ans)

else:
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
        u_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan Portal for IT"):
            if u_in:
                st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.link_button("Go to Official Listing", u_in)
