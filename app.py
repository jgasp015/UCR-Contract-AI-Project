import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- 1. SESSION STATE INITIALIZATION ---
def init_state():
    defaults = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'analysis_mode': "Standard",
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 GROQ_API_KEY missing in Secrets!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    """Factual, list-based extraction without greetings or filler."""
    if not full_text: return "No document data found."
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a Government Data Extractor. Today is April 20, 2026. RULES: No greetings. No intros. No explanations. Use Markdown bullets. Be extremely concise."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:15000]}"} # Limit context to prevent crashes
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "Extraction failed."

def scrape_agency_bids(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        found = []
        for row in soup.find_all('tr'):
            text = row.get_text(separator=' ', strip=True)
            if any(m in text.lower() for m in ["rfb", "rfp", "bid", "solicitation"]):
                found.append({"name": text[:100].upper(), "full_text": text})
        return found[:10]
    except: return []

# --- 3. UI LAYIC ---
st.title("🏛️ Public Sector Contract Analyzer")

# SIDEBAR
with st.sidebar:
    if st.button("🏠 Start Over / Home"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- VIEW 1: ANALYSIS ---
if st.session_state.active_bid_text:
    if st.button("⬅️ Back to Results"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # SILENT DATA GATHERING
    if not st.session_state.agency_name:
        with st.status("🔍 Initializing Analysis..."):
            st.session_state.agency_name = deep_query(doc, "Which Government Agency is this? ONLY the name.")
            st.session_state.project_title = deep_query(doc, "What is the project name? ONLY the name.")
            raw_date = deep_query(doc, "Deadline? (MM/DD/YYYY). If none, say Not Specified.")
            st.session_state.detected_due_date = raw_date
            
            # Logic for Status
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # HEADER (LOCKED TO TOP)
    header_container = st.container()
    if st.session_state.status_flag == "OPEN":
        header_container.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        header_container.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    header_container.markdown(f"### {st.session_state.agency_name}")
    header_container.markdown(f"**Project:** {st.session_state.project_title}")
    header_container.divider()

    # TABS (NO GAP)
    if not st.session_state.summary_ans:
        with st.status("🚀 Processing Detailed Tabs..."):
            st.session_state.bid_details = deep_query(doc, "List Solicitation #, Buyer Name, Email, and Phone.")
            st.session_state.summary_ans = deep_query(doc, "Bulleted list of goals.")
            st.session_state.tech_ans = deep_query(doc, "Bulleted list of software/hardware specs. Be specific.")
            st.session_state.submission_ans = deep_query(doc, "Steps to apply.")
            st.session_state.compliance_ans = deep_query(doc, "Insurance/legal requirements.")
            st.session_state.award_ans = deep_query(doc, "How they pick a winner.")
            st.rerun()

    t_details, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs([
        "📋 Bid Details", "📖 Project Plan", "🛠️ Technology", "📝 Application", "⚖️ Legal", "💰 Award"
    ])
    
    t_details.write(st.session_state.bid_details)
    t_plan.info(st.session_state.summary_ans)
    t_tech.success(st.session_state.tech_ans)
    t_apply.warning(st.session_state.submission_ans)
    t_legal.error(st.session_state.compliance_ans)
    t_award.write(st.session_state.award_ans)

# --- VIEW 2: LIST RESULTS ---
elif st.session_state.all_bids:
    st.write("### Found Opportunities")
    for b in st.session_state.all_bids:
        if st.button(b['name']):
            st.session_state.active_bid_text = b['full_text']
            st.session_state.active_bid_name = b['name']
            st.rerun()

# --- VIEW 3: HOME ---
else:
    tab1, tab2, tab3 = st.tabs(["📄 Search Projects", "📊 Performance", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            reader = PdfReader(up)
            st.session_state.active_bid_text = "".join([p.extract_text() for p in reader.pages])
            st.session_state.active_bid_name = up.name
            st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            reader = PdfReader(up_c)
            st.session_state.active_bid_text = "".join([p.extract_text() for p in reader.pages])
            st.session_state.active_bid_name = up_c.name
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with tab3:
        url_in = st.text_input("Enter Portal URL:")
        if st.button("Scan Portal"):
            st.session_state.all_bids = scrape_agency_bids(url_in)
            st.rerun()
