import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- 1. SILOED SESSION STATE ---
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

# --- 2. CORE AI ENGINE (PROTECTED) ---
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

# --- 3. UNIVERSAL PORTAL SCRAPER (CLEANED) ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # IT Keywords for filtering
        it_k = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "HARDWARE"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in it_k):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_id = link.get_text(strip=True)
                    # Dynamic ID extraction
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    clean_id = id_match.group(1) if id_match else bid_id
                    
                    hits.append({
                        "id": bid_id, 
                        "title": cols[1].get_text(strip=True).split("Commodity:")[0].strip(),
                        "url": url if "detail" in url.lower() else f"{url}/detail?id={clean_id}"
                    })
        return hits
    except: return []

# --- 4. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

# THE BACK BUTTON (Only visible when a document is open)
if st.session_state.active_bid_text:
    if st.sidebar.button("⬅️ Back to Main Menu"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        st.info("### 📊 Active Contract Guide")
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "List SLA Uptime and Reports.", "Compliance Expert.")
        st.markdown(st.session_state.report_ans)
    else:
        # Standard Bid Analysis (Manual Upload Results)
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency?", "Name only.")
            st.session_state.project_title = run_ai(doc, "Project?", "Name only.")
            st.rerun()
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        # Rest of your perfect tabs logic here...

else:
    # MAIN MENU (BLANK DEFAULTS)
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t1:
        st.write("### Analyze a Bid PDF")
        m_up = st.file_uploader("Upload Bid Document", type="pdf", key="m_bid")
        if m_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(m_up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
            
    with t2:
        st.write("### Check SLA Reporting Rules")
        s_up = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if s_up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(s_up).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
            
    with t3:
        st.write("### Scan Government Portal")
        # FIXED: BLANK URL BY DEFAULT
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste government portal link here...")
        if st.button("Scan Portal for IT"):
            if u_in:
                with st.spinner("Searching..."):
                    st.session_state.portal_hits = scrape_portal(u_in)
            else: st.warning("Please enter a URL first.")
        
        if st.session_state.portal_hits:
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['title']} ({b['id']})"):
                    st.link_button("Open Official Listing", b['url'])
                    st.info("💡 Download the PDF and upload to 'Bid Document' tab for analysis.")
