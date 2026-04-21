import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION STATE MANAGEMENT (UNTOUCHED) ---
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

# --- SILO 2: AI ENGINE (SHARED UTILITY) ---
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
    except: return "Deep Analysis Failed."

# --- SILO 3: THE FIXED PORTAL ENGINE (DIRECT PDF DOWNLOAD) ---
def scrape_portal(url):
    """Bypasses session blocks by forcing a handshake with the portal root."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        # Handshake: Visit root first to get the necessary ASP.NET cookies
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers)
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "MODEM", "SECURITY"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    # Extract Bid ID from the JS function selectBid('XXXXX')
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    
                    raw_desc = cols[1].get_text(strip=True).replace(bid_num, "")
                    desc = raw_desc.split("Commodity:")[0].strip()
                    comm = raw_desc.split("Commodity:")[1].strip() if "Commodity:" in raw_desc else "Technology"
                    
                    hits.append({
                        "id": bid_num, "desc": desc, "comm": comm,
                        # Build the Direct Controller link that bypasses the JS click requirement
                        "detail_url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

def direct_pdf_harvest(detail_url):
    """Targets the first document in the detail table using direct session headers."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'}
        res = st.session_state.portal_session.get(detail_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # In the LA Portal, the download link is a direct relative path in the first row
        pdf_link = None
        for a in soup.find_all('a', href=True):
            if "GetAttachment" in a['href'] or ".pdf" in a['href'].lower():
                # Correctly join the base URL to create a valid download link
                pdf_link = "https://camisvr.co.la.ca.us" + a['href'] if a['href'].startswith('/') else a['href']
                break
        
        if not pdf_link: return "Attachment access denied. Please click 'View Portal Detail' to download manually."

        # Execute Download
        pdf_res = st.session_state.portal_session.get(pdf_link, headers=headers, timeout=30)
        reader = PdfReader(io.BytesIO(pdf_res.content))
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        return run_ai(text, "Summarize Project Goals, Tech, and Application steps.", "Government IT Analyst.")
    except Exception as e:
        return f"Portal Session Refused: {str(e)}. Use the 'Bid Document' tab for manual analysis."

# --- UI INTERFACE ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_doc_state(); st.rerun()
    # Manual Bid results show here (PROTECTED)
else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; clear_doc_state(); st.rerun()
            
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_cont")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; clear_doc_state(); st.rerun()
            
    with t3:
        u_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Deep Scan Portal for IT"):
            with st.spinner("Bypassing security and finding IT bids..."):
                st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} IT Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.caption(f"📦 {b['comm']}")
                    st.link_button("View Original Detail Page", b['detail_url'])
                    # FIXED BUTTON: This triggers the automated session-bypass download
                    if st.button(f"Analyze Attachment: {b['id']}", key=f"btn_{b['id']}"):
                        with st.spinner("Downloading document via session bypass..."):
                            st.markdown(direct_pdf_harvest(b['detail_url']))
