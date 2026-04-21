import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE INITIALIZATION ---
def init_all_states():
    defaults = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'analysis_mode': "Standard", 'total_saved': 0,
        'agency_name': None, 'project_title': None, 'summary_ans': None,
        'tech_ans': None, 'submission_ans': None, 'compliance_ans': None,
        'award_ans': None, 'report_ans': None, 'status_flag': None, 'detected_due_date': None
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

init_all_states()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "Government Data Extractor. Concise, 1-word or short points. NO INTROS."
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:12000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Not Specified"

def scrape_stable_bids(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        found_bids = []
        for row in soup.find_all('tr'):
            text = row.get_text(separator=' ', strip=True)
            if any(marker in text.lower() for marker in ["rfb-is-", "rfp-", "solicitation"]):
                found_bids.append({"name": text[:150].upper(), "full_text": text})
        return found_bids[:10]
    except: return []

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Return Home"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS VIEW ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to List"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    if not st.session_state.agency_name:
        with st.spinner("Processing Document..."):
            st.session_state.agency_name = deep_query(doc, "Agency name? ONLY name.")
            st.session_state.project_title = deep_query(doc, "Project title? ONLY name.")
            st.session_state.detected_due_date = deep_query(doc, "Deadline? (MM/DD/YYYY).")
            st.session_state.status_flag = deep_query(doc, "Status: OPEN, CLOSED, or AWARDED?").upper()
            st.rerun()

    # --- THE FIX: Safety check for the status_flag to prevent TypeError ---
    status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"

    if "OPEN" in status:
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    elif "AWARDED" in status:
        st.info(f"● AWARDED | Project Completed")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")

    st.markdown(f"### {st.session_state.agency_name}")
    st.markdown(f"**{st.session_state.project_title}**")
    st.divider()

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Analyzing Standards..."):
                st.session_state.report_ans = deep_query(doc, "Summarize: Uptime %, Fix times, Penalty credits.")
                st.session_state.total_saved += 60
                st.rerun()
        st.markdown(st.session_state.report_ans)
    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Performing Deep Scan..."):
                st.session_state.summary_ans = deep_query(doc, "Project goal.")
                st.session_state.tech_ans = deep_query(doc, "Required gear.")
                st.session_state.submission_ans = deep_query(doc, "Steps to apply.")
                st.session_state.compliance_ans = deep_query(doc, "Insurance/legal.")
                st.session_state.award_ans = deep_query(doc, "Winner selection.")
                st.session_state.total_saved += 120
                st.rerun()

        tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        tabs[0].info(st.session_state.summary_ans)
        tabs[1].success(st.session_state.tech_ans)
        tabs[2].warning(st.session_state.submission_ans)
        tabs[3].error(st.session_state.compliance_ans)
        tabs[4].write(st.session_state.award_ans)

# --- VIEW 2: SEARCH RESULTS ---
elif st.session_state.all_bids:
    if st.button("⬅️ Back to Search"):
        st.session_state.all_bids = []
        st.rerun()
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"### 📦 {bid['name']}")
            if st.button("Analyze", key=f"bid_{idx}"):
                st.session_state.active_bid_text = bid['full_text']
                st.session_state.analysis_mode = "Standard"
                st.rerun()

# --- VIEW 3: INITIAL SEARCH ---
else:
    t1, t2, t3 = st.tabs(["📄 Bid", "📊 Contract", "🔗 Scan"])
    with t1:
        up_bid = st.file_uploader("Upload Bid PDF", type="pdf")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    with t2:
        up_rep = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_rep:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_rep).pages])
            st.session_state.analysis_mode = "Reporting"; st.rerun()
    with t3:
        url = st.text_input("Portal Link:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan Portal"):
            st.session_state.all_bids = scrape_stable_bids(url); st.rerun()
