import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io
import re

# --- 1. SESSION STATE (STRICTLY ISOLATED) ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'agency_name': None, 'project_title': None, 
        'detected_due_date': None, 'summary_ans': None, 'tech_ans': None, 
        'submission_ans': None, 'compliance_ans': None, 'award_ans': None, 
        'bid_details': None, 'report_ans': None
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

# --- 2. CORE ENGINES (MANUAL UPLOADS - UNTOUCHED) ---
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
    except: return "Deep Analysis Pending..."

# --- 3. THE PORTAL ENGINE (REBUILT FOR STABILITY) ---
def scrape_portal_it_bids(url):
    """Deep-scrapes the list for IT keywords and extracts actual Bid Descriptions."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        it_keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "SECURITY", "MODEM"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in it_keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    # Extract Internal ID for deep links
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    
                    full_desc = cols[1].get_text(strip=True).replace(bid_num, "")
                    description = full_desc.split("Commodity:")[0].strip()
                    commodity = full_desc.split("Commodity:")[1].strip() if "Commodity:" in full_desc else "IT Service"
                    
                    hits.append({
                        "id": bid_num, 
                        "title": description, 
                        "comm": commodity,
                        "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

# --- 4. UI INTERFACE ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_doc_state(); st.rerun()
    # (Results for manual PDF uploads appear here - siloed and safe)
else:
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t_bid:
        st.write("### Analyze a specific Bid PDF")
        m_up = st.file_uploader("Upload Bid PDF", type="pdf", key="manual_bid")
        if m_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(m_up).pages])
            st.session_state.analysis_mode = "Standard"; clear_doc_state(); st.rerun()
            
    with t_sla:
        st.write("### Check Active Contract SLA Rules")
        s_up = st.file_uploader("Upload Contract PDF", type="pdf", key="manual_sla")
        if s_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(s_up).pages])
            st.session_state.analysis_mode = "Reporting"; clear_doc_state(); st.rerun()
            
    with t_url:
        st.write("### Scan Government Portals for IT Opportunities")
        u_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Search for IT & Software"):
            with st.spinner("Filtering portal for technology matches..."):
                st.session_state.portal_hits = scrape_portal_it_bids(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} IT Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['title']} ({b['id']})"):
                    st.write(f"**📦 Commodity:** {b['comm']}")
                    # This button opens the actual government detail page
                    st.link_button("1. View Official Bid & PDF", b['url'])
                    st.divider()
                    st.write("💡 **Pro-Tip:** Download the Bid PDF from the link above and upload it to the **'Bid Document'** tab for a deep analysis of goals, tech, and legal rules.")
