import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE (STRICTLY ISOLATED & PERMANENT) ---
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

# --- SILO 2: AI ENGINES (MOM-TEST FOR BID, HIGH-CONTEXT FOR PERFORMANCE) ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    if context_slice == "start": ctx = text[:15000]
    else: ctx = text[:10000] + "\n[...]\n" + text[-10000:]
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}],
        "temperature": 0.0
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return r.json()['choices'][0]['message']['content'].strip()

# --- SILO 3: THE FIXED AGENCY URL SCANNER (TRIPLE HANDSHAKE) ---
def scrape_portal(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://camisvr.co.la.ca.us/LACoBids/'
        }
        # Step 1: Hit root for cookies
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers, timeout=10)
        # Step 2: Hit the search page
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList", headers=headers, timeout=10)
        # Step 3: Get the actual requested URL
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        it_k = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "MODEM", "SECURITY", "HARDWARE"]
        hits = []
        for row in soup.find_all('tr'):
            txt = row.get_text().upper()
            if any(k in txt for k in it_k):
                cols = row.find_all('td')
                link = row.find('a', href=True)
                if link and len(cols) >= 2:
                    bid_num = link.get_text(strip=True)
                    id_match = re.search(r"\'(\d+)\'", link['href'])
                    bid_id = id_match.group(1) if id_match else ""
                    hits.append({
                        "id": bid_num, 
                        "desc": cols[1].get_text(strip=True).split("Commodity:")[0].strip(),
                        "url": f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"
                    })
        return hits
    except: return []

# --- SILO 4: UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis(); st.rerun()
    
    doc = st.session_state.active_bid_text
    if st.session_state.analysis_mode == "Reporting":
        # PERFECT PERFORMANCE VIEW
        st.subheader("📊 Performance, Penalties & Stop-Clock Rules")
        if not st.session_state.report_ans:
            prompt = "Explain: 1. HOW to report, 2. Uptime targets, 3. PENALTIES, 4. STOP-CLOCK conditions, 5. Monthly reports."
            st.session_state.report_ans = run_ai(doc, prompt, "Contract Compliance Expert. High Detail.", "full")
        st.markdown(st.session_state.report_ans)
    else:
        # PERFECT MOM-TEST BID VIEW
        if not st.session_state.agency_name:
            st.session_state.agency_name = run_ai(doc, "Agency Name?", "Name only.", "start")
            st.session_state.project_title = run_ai(doc, "Project Name?", "Name only.", "start")
            st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
            st.rerun()
        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
        
        if not st.session_state.summary_ans:
            st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
            st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test points.", "full")
            st.session_state.tech_ans = run_ai(doc, "Specific tools needed? Max 5 points.", "List items.", "full")
            st.session_state.submission_ans = run_ai(doc, "How to apply?", "1, 2, 3.", "start")
            st.session_state.compliance_ans = run_ai(doc, "Simple rules/Insurance?", "Mom-test points.", "full")
            st.session_state.award_ans = run_ai(doc, "How to win?", "Simple list.", "full")
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].markdown(st.session_state.bid_details); tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans); tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans); tabs[5].write(st.session_state.award_ans)

else:
    # --- SILO 5: MAIN MENU (RESTORED URL SCANNER) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_sla, t_url = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    
    with t_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    with t_sla:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; reset_analysis(); st.rerun()
    with t_url:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            if u_in:
                with st.spinner("Establishing secure handshake..."):
                    st.session_state.portal_hits = scrape_portal(u_in)
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} IT Opportunities:")
            for b in st.session_state.portal_hits:
                with st.expander(f"🖥️ {b['desc']} ({b['id']})"):
                    st.link_button("Open Listing", b['url'])
                    st.info("💡 Download the PDF from the portal and upload it to the 'Bid Document' tab.")
