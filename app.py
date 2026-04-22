import streamlit as st
import requests
import time
from pypdf import PdfReader
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (LOCKED & PRESERVED) ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'analysis_mode' not in st.session_state: st.session_state.analysis_mode = "Standard" 
if 'total_saved' not in st.session_state: st.session_state.total_saved = 480 

# All logic keys
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'report_ans', 'status_flag', 'agency_name', 'project_title', 'detected_due_date']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, persona="Mom-Test"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": f"You are a helpful assistant. Use the '{persona}': explain things simply with zero jargon. If data is missing, say 'Not found'. NO INTROS."
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:20000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "⚠️ Connection error. Click again."

def scrape_portal(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        hits = []
        for row in soup.find_all('tr'):
            text = row.get_text(separator=' ', strip=True).upper()
            if any(k in text for k in ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK"]):
                hits.append({"desc": text[:100], "id": "Portal Item"})
        return hits
    except: return []

# --- 3. UI LOGIC ---
st.title("🏛️ Reporting Tool")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Return Home"):
        for k in st.session_state.keys():
            if k != 'total_saved': st.session_state[k] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- VIEW 1: ANALYSIS MODE (ACTIVE DOCUMENT) ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        # --- PERFORMANCE REPORTING LOGIC ---
        st.subheader("📊 Contract Performance Analysis")
        if not st.session_state.report_ans:
            with st.status("🔍 Checking SLAs & Penalties..."):
                prompt = "Summarize: 1. Uptime % required, 2. Late penalties, 3. Stop-clock rules, 4. Reporting dates."
                st.session_state.report_ans = deep_query(doc, prompt, persona="Auditor-Persona")
        st.info(st.session_state.report_ans)
    
    else:
        # --- STANDARD BID LOGIC (THE ONE THAT WORKS) ---
        if not st.session_state.agency_name:
            with st.status("🏗️ Reading Document..."):
                st.session_state.agency_name = deep_query(doc, "Agency Name?")
                st.session_state.project_title = deep_query(doc, "Project Title?")
                st.session_state.detected_due_date = deep_query(doc, "Deadline date?")
                st.session_state.status_flag = deep_query(doc, "Is this OPEN, CLOSED, or AWARDED?").upper()
            st.rerun()

        status = st.session_state.status_flag if st.session_state.status_flag else "UNKNOWN"
        if "OPEN" in status: st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        else: st.error(f"● {status} | Deadline: {st.session_state.detected_due_date}")

        st.markdown(f"### {st.session_state.agency_name}")
        st.markdown(f"**{st.session_state.project_title}**")
        st.divider()

        tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Rules", "💰 Winner"])
        with tabs[0]:
            if not st.session_state.summary_ans: st.session_state.summary_ans = deep_query(doc, "3 bullet points on the goal.")
            st.info(st.session_state.summary_ans)
        with tabs[1]:
            if not st.session_state.tech_ans: st.session_state.tech_ans = deep_query(doc, "Required computers/tools?")
            st.success(st.session_state.tech_ans)
        with tabs[2]:
            if not st.session_state.submission_ans: st.session_state.submission_ans = deep_query(doc, "3 easy steps to apply.")
            st.warning(st.session_state.submission_ans)
        with tabs[3]:
            if not st.session_state.compliance_ans: st.session_state.compliance_ans = deep_query(doc, "Insurance and big rules?")
            st.error(st.session_state.compliance_ans)
        with tabs[4]:
            if not st.session_state.award_ans: st.session_state.award_ans = deep_query(doc, "How do they choose the winner?")
            st.write(st.session_state.award_ans)

# --- VIEW 2: MAIN MENU (RESTORED ALL TABS) ---
else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Performance Standards", "🔗 Agency URL"])
    
    with t1:
        up_bid = st.file_uploader("Upload Bid PDF", type="pdf", key="up_bid_restore")
        if up_bid:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_bid).pages])
            st.session_state.analysis_mode = "Standard"
            st.rerun()
            
    with t2:
        up_perf = st.file_uploader("Upload Signed Contract PDF", type="pdf", key="up_perf_restore")
        if up_perf:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up_perf).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
            
    with t3:
        u_in = st.text_input("Agency URL:", value="", placeholder="Paste link here...")
        if st.button("Scan Portal"):
            st.session_state.all_bids = scrape_portal(u_in)
        
        if st.session_state.all_bids:
            for b in st.session_state.all_bids:
                st.write(f"🖥️ {b['desc']}")
