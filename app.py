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

# --- VAULT 3: THE AUTOMATED PDF HARVESTER (FIXED FOR LA COUNTY BUTTONS) ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers)
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # MASTER IT/HARDWARE KEYWORDS
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "SECURITY", "MODEM", "CELLULAR"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    
                    raw_desc = cols[1].get_text(strip=True).replace(bid_num, "")
                    desc = raw_desc.split("Commodity:")[0].strip()
                    comm = raw_desc.split("Commodity:")[1].strip() if "Commodity:" in raw_desc else "Technology"
                    
                    hits.append({
                        "id": bid_num, "desc": desc, "comm": comm,
                        "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

def automated_pdf_download(bid_detail_url):
    """Simulates clicking the 'Download' button for the first PDF in the list."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'}
        res = st.session_state.portal_session.get(bid_detail_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # FIND THE FIRST DOWNLOAD BUTTON THAT IS A PDF
        pdf_link = None
        # Tables on this portal usually list files in rows with a 'Download' button
        for row in soup.find_all('tr'):
            row_txt = row.get_text().lower()
            if "application/pdf" in row_txt:
                a_tag = row.find('a', href=True)
                if a_tag:
                    pdf_link = urljoin("https://camisvr.co.la.ca.us", a_tag['href'])
                    break # Stop at the first (Bid Document)
        
        if not pdf_link:
            return "Failed to locate the first PDF. Please verify the portal detail page has attachments."

        # Download PDF using established session
        pdf_res = st.session_state.portal_session.get(pdf_link, headers=headers, timeout=30)
        reader = PdfReader(io.BytesIO(pdf_res.content))
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        return run_ai(text, "Summarize Goals, Tech Needed, and How to apply.", "Government IT Analyst.")
    except Exception as e:
        return f"Download failed: {str(e)}. Use the 'Bid Document' tab for manual PDF upload."

# --- UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_doc_state(); st.rerun()
    # Manual PDF logic remains exactly as it was...
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
        u_in = st.text_input("Agency Portal URL:", placeholder="https://camisvr.co.la.ca.us/...")
        if st.button("Find IT/Hardware Bids"):
            if u_in:
                with st.spinner("Finding opportunities..."):
                    st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.caption(f"📦 {b['comm']}")
                    st.link_button("View Portal Detail", b['url'])
                    # FIXED: This button now auto-downloads the first PDF it finds
                    if st.button(f"Auto-Analyze First PDF: {b['id']}", key=f"auto_{b['id']}"):
                        with st.spinner("Downloading and analyzing first document..."):
                            analysis = automated_pdf_download(b['url'])
                            st.markdown(analysis)
