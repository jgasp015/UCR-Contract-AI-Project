import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io
import re

# --- 1. VAULT: SESSION INITIALIZATION (ISOLATED) ---
if 'portal_hits' not in st.session_state: st.session_state.portal_hits = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"
if 'portal_session' not in st.session_state: st.session_state.portal_session = requests.Session()

def clear_data():
    for key in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 
                'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans']:
        if key in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. VAULT: MANUAL BID & REPORTING ENGINES (UNTOUCHED PERFECTION) ---
def run_ai_query(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:15000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return "N/A"

# --- 3. VAULT: THE WEB SCRAPER ENGINE (FIXED SECTION) ---
def scrape_portal_list(url):
    """Establishes a persistent session to prevent 'Object Reference' errors."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        # Step 1: Hit home to get cookies
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers)
        # Step 2: Get the actual list
        r = st.session_state.portal_session.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "SECURITY"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in keywords):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    # Extract Bid ID from JavaScript: selectBid('2648...')
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    
                    raw_desc = cols[1].get_text(strip=True).replace(bid_num, "")
                    desc = raw_desc.split("Commodity:")[0].strip()
                    comm = raw_desc.split("Commodity:")[1].strip() if "Commodity:" in raw_desc else "IT"
                    
                    hits.append({
                        "id": bid_num, "desc": desc, "comm": comm,
                        "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

def analyze_web_bid(bid_url):
    """Goes inside the JS-heavy portal, extracts the PDF, and analyzes it."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'}
        res = st.session_state.portal_session.get(bid_url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Locate the PDF attachment link
        pdf_url = None
        for a in soup.find_all('a', href=True):
            if any(x in a['href'].lower() for x in [".pdf", "getattachment"]):
                pdf_url = urljoin("https://camisvr.co.la.ca.us", a['href'])
                break
        
        if not pdf_url: return "No PDF found on detail page. Please use 'Bid Document' for manual upload."

        # Download and Parse PDF
        pdf_res = st.session_state.portal_session.get(pdf_url, headers=headers)
        reader = PdfReader(io.BytesIO(pdf_res.content))
        full_text = "".join([p.extract_text() for p in reader.pages])

        # Run Analysis
        sys_msg = "You are a Government IT Bid Analyst. Use vertical '-' bullet points."
        analysis = run_ai_query(full_text, "List: 1. Project Goals, 2. Required Tech, 3. Legal/Conduct rules.", sys_msg)
        return analysis
    except Exception as e: return f"Deep scan blocked by portal security: {str(e)}"

# --- 4. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])

with tab1: # MANUAL UPLOAD (PROTECTED)
    up = st.file_uploader("Upload Bid PDF", type="pdf", key="bid_vault")
    if up:
        text = "".join([p.extract_text() for p in PdfReader(up).pages])
        st.subheader("Manual Bid Analysis")
        st.info(run_ai_query(text, "Summarize project goals and required software.", "Public Records Assistant."))

with tab2: # SLA PERFORMANCE (PROTECTED)
    up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="sla_vault")
    if up_c:
        text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
        st.subheader("Contract Reporting Rules")
        st.warning(run_ai_query(text, "List SLA Uptime %, Fix Times, and Monthly Reports.", "Compliance Expert."))

with tab3: # WEB SCRAPER (FIXED)
    url_in = st.text_input("Enter Portal URL:", value="", placeholder="Paste government URL...")
    if st.button("Deep Scan Portal"):
        if url_in:
            with st.spinner("Establishing secure session..."):
                st.session_state.portal_hits = scrape_portal_list(url_in)
    
    if st.session_state.portal_hits:
        st.success(f"Found {len(st.session_state.portal_hits)} IT Opportunities:")
        for bid in st.session_state.portal_hits:
            with st.expander(f"🖥️ {bid['desc']} ({bid['id']})"):
                st.caption(f"📦 {bid['comm']}")
                st.link_button("Open Listing", bid['url'])
                if st.button(f"Analyze Document: {bid['id']}", key=f"btn_{bid['id']}"):
                    with st.spinner("Extracting hidden PDF..."):
                        st.markdown(analyze_web_bid(bid['url']))
