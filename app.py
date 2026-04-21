import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- 1. CORE STATE ---
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard"

def reset_analysis():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
            'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
    if k not in st.session_state: st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE ENGINE (ZERO FRICTION) ---
def run_ai(text, prompt, system_msg):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Use a direct, short context to avoid timeouts
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ Service busy. Refreshing..."

# --- 3. URL SCANNER (DO NOT TOUCH - WORKING) ---
def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        session = requests.Session()
        session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers, timeout=5)
        r = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in ["SOFTWARE", "IT ", "TECHNOLOGY", "SAAS", "DATA"]):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    hits.append({"id": bid_num, "desc": cols[1].get_text(strip=True), "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"})
        return hits
    except: return []

# --- 4. UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # CONTRACT PERFORMANCE
        if not st.session_state.report_ans:
            st.session_state.report_ans = run_ai(doc, "List: Reporting steps, Uptime targets, Penalties, Stop-Clock rules.", "Compliance Officer.")
        st.markdown(st.session_state.report_ans)
    else:
        # BID DOCUMENT (THE FAST WAY)
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency?", "Name only.")
            st.session_state.project_title = run_ai(doc, "Project?", "Name only.")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.")
            st.rerun()

        st.success(f"● {st.session_state.agency_name} | 📅 {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)

        if not st.session_state.summary_ans:
            st.session_state.summary_ans = run_ai(doc, "Goals?", "Mom-test simple.")
            st.session_state.tech_ans = run_ai(doc, "Tech?", "Simple list.")
            st.session_state.submission_ans = run_ai(doc, "Steps to apply?", "1,2,3.")
            st.session_state.compliance_ans = run_ai(doc, "Rules?", "Simple.")
            st.session_state.award_ans = run_ai(doc, "Winner?", "Simple.")
            st.rerun()

        tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].info(st.session_state.summary_ans); tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans); tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

else:
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
    with t3:
        u_in = st.text_input("Agency URL:")
        if st.button("Scan Portal"):
            st.session_state.portal_hits = scrape_portal(u_in)
        if st.session_state.portal_hits:
            for b in st.session_state.portal_hits:
                with st.expander(f"{b['desc']}"): st.link_button("Open Listing", b['url'])
