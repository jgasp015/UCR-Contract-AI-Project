import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'agency_name': None, 'project_title': None, 
        'detected_due_date': None, 'summary_ans': None, 'tech_ans': None, 
        'submission_ans': None, 'compliance_ans': None, 'award_ans': None, 
        'bid_details': None, 'report_ans': None, 'total_saved': 0
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved':
            del st.session_state[key]
    init_state()
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: AI ENGINE (STRICT PERSONA SEPARATION) ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Slice text to keep it fast and under token limits
    ctx = text[:12000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"{system_msg} Respond ONLY with short, simple bullet points. No jargon."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ AI currently busy. Please refresh."

# --- SILO 3: THE FIXED URL SCANNER ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        it_keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "SECURITY", "HARDWARE"]
        hits = []
        
        # LACoBids usually uses <tr> for rows. We look for keywords in the text.
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in it_keywords):
                cols = row.find_all('td')
                if len(cols) >= 2:
                    # Clean the ID and Description
                    bid_id = cols[0].get_text(strip=True)
                    desc = cols[1].get_text(strip=True).split("Commodity:")[0].strip()
                    hits.append({"id": bid_id, "desc": desc})
        return hits
    except Exception as e:
        return [{"id": "Error", "desc": f"Could not connect to portal: {str(e)}"}]

# --- SILO 4: UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.session_state.active_bid_text:
        if st.button("🏠 Home / Back"):
            hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # --- REPORTING MODE (CONTRACT PERFORMANCE) ---
    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance & SLA Reporting Tool")
        if not st.session_state.report_ans:
            with st.status("🔍 Extracting Performance Rules..."):
                # Forced Auditor Persona
                prompt = "What are the specific Uptime targets, Response times, and Penalties for being down? Use simple words."
                st.session_state.report_ans = run_ai(doc, prompt, "You are a Contract Performance Auditor. Focus ONLY on SLAs and penalties.")
                st.session_state.total_saved += 60
            st.rerun()
        st.info(st.session_state.report_ans)

    # --- STANDARD MODE (NEW BID) ---
    else:
        if not st.session_state.agency_name:
            with st.status("🏗️ Identifying Bid..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Government Data Extractor. Name only.")
                st.session_state.project_title = run_ai(doc, "Project Title?", "Government Data Extractor. Name only.")
                st.session_state.detected_due_date = run_ai(doc, "Deadline date?", "Date only.")
            st.rerun()

        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        
        if not st.session_state.summary_ans:
            with st.status("🚀 Deep Scanning..."):
                st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.")
                st.session_state.summary_ans = run_ai(doc, "What are the 3 main goals?", "Mom-test simplicity.")
                st.session_state.tech_ans = run_ai(doc, "What computers/software is needed?", "Simple list.")
                st.session_state.submission_ans = run_ai(doc, "How to apply? 1,2,3.", "Guide.")
                st.session_state.compliance_ans = run_ai(doc, "Rules/Insurance?", "Simple.")
                st.session_state.award_ans = run_ai(doc, "How do they choose the winner?", "Simple.")
                st.session_state.total_saved += 120
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].markdown(st.session_state.bid_details); tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans); tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans); tabs[5].write(st.session_state.award_ans)

else:
    st.title("🏛️ Reporting Tool")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Performance Standards", "🔗 Agency URL"])
    
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
            
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
            
    with t3:
        # THE FIX: Empty URL box and improved scanner
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            if u_in:
                st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.info("💡 Download the PDF from the portal and upload it to the 'Bid Document' tab for a full analysis.")
