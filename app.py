import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# --- 1. SESSION STATE ---
def init_state():
    keys = {
        'all_bids': [], 'active_bid_text': None, 'active_bid_name': None,
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'analysis_mode': "Standard",
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt):
    """Strictly factual fragments. No intros. No labels."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a Government Data Extractor. RULES: 1. NO INTROS. 2. NO LABELS. 3. Bullets only for tabs. 4. Single words for names."
            },
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text[:10000]}"}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return response.json()['choices'][0]['message']['content'].strip()
    except: return "N/A"

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
                found.append({"name": text[:80].upper(), "full_text": text})
        return found[:10]
    except: return []

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    if st.button("🏠 Home"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        st.rerun()

    doc = st.session_state.active_bid_text

    # SILENT EXTRACTION
    if not st.session_state.agency_name:
        with st.status("Gathering Data..."):
            # Clean strings to remove ANY bullets or extra lines the AI might include
            st.session_state.agency_name = deep_query(doc, "Agency name?").split('\n')[0].replace('- ', '')
            st.session_state.project_title = deep_query(doc, "Project title?").split('\n')[0].replace('- ', '')
            raw_date = deep_query(doc, "Deadline? (MM/DD/YYYY)").split('\n')[0].replace('- ', '')
            st.session_state.detected_due_date = raw_date
            
            today = datetime(2026, 4, 20)
            try:
                clean_date = datetime.strptime(raw_date, "%m/%d/%Y")
                st.session_state.status_flag = "CLOSED" if clean_date < today else "OPEN"
            except:
                st.session_state.status_flag = "OPEN"
            st.rerun()

    # --- CLEAN HEADER (Zero Extra Content) ---
    if st.session_state.status_flag == "OPEN":
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
    else:
        st.error(f"● CLOSED | Deadline: {st.session_state.detected_due_date}")
    
    st.subheader(st.session_state.project_title)
    st.write(f"**Agency:** {st.session_state.agency_name}")
    st.divider()

    # --- TABS ---
    if not st.session_state.summary_ans:
        with st.status("🚀 Processing Details..."):
            st.session_state.bid_details = deep_query(doc, "List Solicitation #, Buyer, Email, Phone.")
            st.session_state.summary_ans = deep_query(doc, "Bulleted project goals.")
            st.session_state.tech_ans = deep_query(doc, "Bulleted tech specs.")
            st.session_state.submission_ans = deep_query(doc, "Bulleted steps to apply.")
            st.session_state.compliance_ans = deep_query(doc, "Bulleted insurance/legal rules.")
            st.session_state.award_ans = deep_query(doc, "Winner selection facts.")
            st.rerun()

    t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
    t_det.write(st.session_state.bid_details)
    t_plan.info(st.session_state.summary_ans)
    t_tech.success(st.session_state.tech_ans)
    t_apply.warning(st.session_state.submission_ans)
    t_legal.error(st.session_state.compliance_ans)
    t_award.write(st.session_state.award_ans)

elif st.session_state.all_bids:
    for b in st.session_state.all_bids:
        if st.button(b['name']):
            st.session_state.active_bid_text = b['full_text']
            st.rerun()
else:
    tab1, tab2, tab3 = st.tabs(["📄 Search", "📊 Reporting", "🔗 Agency URL"])
    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.rerun()
    with tab2:
        up_c = st.file_uploader("Upload Reporting PDF", type="pdf")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
    with tab3:
        url_in = st.text_input("Agency Portal URL:")
        if st.button("Scan Portal"):
            st.session_state.all_bids = scrape_agency_bids(url_in)
            st.rerun()
