import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io
import re

# --- VAULT 1: ISOLATED SESSION STATE ---
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

# --- VAULT 2: CORE AI ENGINE (FOR MANUAL UPLOADS) ---
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
    except: return "Analysis unavailable."

# --- VAULT 3: THE WEB HARVESTER (FIXED FOR HIDDEN DOCUMENTS) ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # Visit home first to bypass security/session checks
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers)
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Comprehensive keyword list to find IT and Hardware items
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "SECURITY", "HARDWARE"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    # Extract internal ID for the detail page
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

def deep_harvest_document(bid_url):
    """Deep scan for hidden PDF objects or attachment IDs."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'}
        res = st.session_state.portal_session.get(bid_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for PDF links or hidden attachment IDs
        pdf_url = None
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if any(x in href for x in [".pdf", "getattachment", "download", "attachmentid"]):
                pdf_url = urljoin("https://camisvr.co.la.ca.us", a['href'])
                break
        
        if not pdf_url: return "No downloadable file was detected. The portal may be blocking automated access to this specific bid."

        # Attempt to download the document using the active session
        pdf_res = st.session_state.portal_session.get(pdf_url, headers=headers, timeout=25)
        reader = PdfReader(io.BytesIO(pdf_res.content))
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        if len(text) < 100: return "The document appears to be an image scan. Manual analysis required."

        return run_ai(text, "List Project Goals, Tech Required, and Award Criteria.", "Government IT Analyst.")
    except Exception as e: return f"Access denied by portal: {str(e)}"

# --- UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_doc_state(); st.rerun()
    
    doc = st.session_state.active_bid_text
    if st.session_state.analysis_mode == "Reporting":
        st.info("### 📊 Active Contract Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "List SLA Uptime and Reports.", "Compliance Expert.")
        st.markdown(st.session_state.report_ans)
    else:
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency Name?", "Return ONLY name.")
            st.session_state.project_title = run_ai(doc, "Project Name?", "Return ONLY name.")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.")
            st.rerun()
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        
        t1, t2, t3, t4, t5, t6 = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        # Standard Bid Logic calls here...
else:
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
        u_in = st.text_input("Enter Government Portal URL:", placeholder="https://camisvr.co.la.ca.us/...")
        if st.button("Scan Portal for IT"):
            if u_in:
                with st.spinner("Finding opportunities..."):
                    st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.caption(f"📦 {b['comm']}")
                    st.link_button("Open Listing", b['url'])
                    if st.button(f"Deep Analyze Document: {b['id']}", key=f"deep_{b['id']}"):
                        with st.spinner("Harvesting hidden document..."):
                            st.markdown(deep_harvest_document(b['url']))
