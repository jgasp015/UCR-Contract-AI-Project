import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io
import re

# --- 1. SILO: SESSION & STATE MANAGEMENT ---
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

def clear_doc_state():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. SILO: CORE AI ENGINE (SHARED BY ALL SECTIONS BUT ISOLATED CALLS) ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:18000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "Analysis currently unavailable."

# --- 3. SILO: WEB SCRAPING & DEEP ANALYSIS ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # Establish session first
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers)
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "SECURITY", "HARDWARE"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    # Extract ID from JS
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    
                    full_desc = cols[1].get_text(strip=True).replace(bid_num, "")
                    desc = full_desc.split("Commodity:")[0].strip()
                    comm = full_desc.split("Commodity:")[1].strip() if "Commodity:" in full_desc else "Technology"
                    
                    hits.append({
                        "id": bid_num, "desc": desc, "comm": comm,
                        "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

def deep_analyze_url(bid_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'}
        res = st.session_state.portal_session.get(bid_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        pdf_url = None
        for a in soup.find_all('a', href=True):
            if any(x in a['href'].lower() for x in [".pdf", "getattachment"]):
                pdf_url = urljoin("https://camisvr.co.la.ca.us", a['href'])
                break
        
        if not pdf_url: return "No PDF found on page. Please use the 'Bid Document' tab to upload manually."

        pdf_res = st.session_state.portal_session.get(pdf_url, headers=headers)
        reader = PdfReader(io.BytesIO(pdf_res.content))
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        return run_ai(text, "Summarize Project Goals, Tech Required, and Legal Rules.", "IT Government Bid Analyst. Use '-' bullet points.")
    except Exception as e: return f"Error accessing document: {str(e)}"

# --- 4. UI: THE UNIFIED PROTECTED INTERFACE ---
st.title("🏛️ Public Sector Contract Analyzer")

# BACK BUTTON LOGIC
if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_doc_state()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # SLA Reporting View
        st.info("### 📊 Active Contract: Reporting Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "List SLA Uptime, Fix Times, and Reports.", "Compliance Expert.")
        st.markdown(st.session_state.report_ans)
    else:
        # Standard Bid View
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency Name?", "Return ONLY name.")
            st.session_state.project_title = run_ai(doc, "Project Name?", "Return ONLY name.")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Return ONLY date.")
            st.rerun()
            
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")

        if not st.session_state.summary_ans:
            st.session_state.bid_details = run_ai(doc, "Solicitation ID and Email.", "Facts only.")
            st.session_state.summary_ans = run_ai(doc, "Project goals?", "Vertical points.")
            st.session_state.tech_ans = run_ai(doc, "Tech needed?", "List items.")
            st.session_state.submission_ans = run_ai(doc, "Steps to apply?", "1, 2, 3.")
            st.session_state.compliance_ans = run_ai(doc, "Legal/Conduct rules?", "Vertical points.")
            st.session_state.award_ans = run_ai(doc, "Award criteria?", "Simple list.")
            st.rerun()

        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t1.markdown(st.session_state.bid_details); t2.info(st.session_state.summary_ans)
        t3.success(st.session_state.tech_ans); t4.warning(st.session_state.submission_ans)
        t5.error(st.session_state.compliance_ans); t6.write(st.session_state.award_ans)

else:
    # MAIN MENU
    tab_manual, tab_sla, tab_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with tab_manual:
        m_up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if m_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(m_up).pages])
            st.session_state.analysis_mode = "Standard"; clear_doc_state(); st.rerun()
            
    with tab_sla:
        s_up = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if s_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(s_up).pages])
            st.session_state.analysis_mode = "Reporting"; clear_doc_state(); st.rerun()
            
    with tab_url:
        u_in = st.text_input("Enter Government Portal URL:", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            if u_in:
                with st.spinner("Finding opportunities..."):
                    st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.caption(f"📦 {b['comm']}")
                    st.link_button("Open Official Portal", b['url'])
                    if st.button(f"Analyze {b['id']}", key=f"deep_{b['id']}"):
                        with st.spinner("Extracting hidden document..."):
                            st.markdown(deep_analyze_url(b['url']))
