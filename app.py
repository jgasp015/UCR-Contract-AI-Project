import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Initialize Session States
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'active_bid_link' not in st.session_state: st.session_state.active_bid_link = None

# Persistent AI Responses
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---
def query_groq(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        data = response.json()
        return data['choices'][0]['message']['content'] if "choices" in data else "⚠️ AI Busy"
    except:
        return "⚠️ Connection Error"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        for key in ['active_bid_text', 'active_bid_link'] + keys:
            st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if not st.session_state.active_bid_text:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        manual_url = st.text_input("Paste Source Link (Optional):")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:5000]
            st.session_state.active_bid_link = manual_url
            st.rerun()
    else:
        # Live Portal mode placeholder logic
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            st.info("Portal scraping active. Select a bid to analyze.")
            # (Insert portal scraping logic here if needed)

# --- 4. INSTANT ANALYSIS AREA ---
if st.session_state.active_bid_text:
    
    # Run analysis automatically if not already done
    if not st.session_state.summary_ans:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Analyzing contract..."):
            # 1. Status
            status_text.text("Checking contract status...")
            st.session_state.status_flag = query_groq(f"Is this bid Awarded, Closed, or Active? Answer in 1 word: {st.session_state.active_bid_text}", "Auditor.")
            progress_bar.progress(20)
            
            # 2. Overview
            status_text.text("Summarizing project goals...")
            st.session_state.summary_ans = query_groq(f"Summarize project scope simply: {st.session_state.active_bid_text}", "Advisor.")
            progress_bar.progress(40)
            
            # 3. Tech Specs
            status_text.text("Extracting technical requirements...")
            st.session_state.tech_ans = query_groq(f"List ONLY IT hardware/software/cabling: {st.session_state.active_bid_text}", "IT Auditor.")
            progress_bar.progress(60)
            
            # 4. Submission
            status_text.text("Identifying deadlines...")
            st.session_state.submission_ans = query_groq(f"Deadlines and submission steps: {st.session_state.active_bid_text}", "Advisor.")
            progress_bar.progress(80)
            
            # 5. Compliance & Award
            status_text.text("Finalizing compliance and financial data...")
            st.session_state.compliance_ans = query_groq(f"Mandatory rules and reporting: {st.session_state.active_bid_text}", "Auditor.")
            st.session_state.award_ans = query_groq(f"Identify Awarded Vendor and Amount: {st.session_state.active_bid_text}", "Financial Auditor.")
            progress_bar.progress(100)
            
            st.session_state.total_saved += 80 
            status_text.empty()
            progress_bar.empty()
            st.rerun()

    # --- DISPLAY RESULTS ---
    if st.session_state.status_flag and "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    st.divider()
    
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])

    with t1:
        st.markdown("#### 📖 Bid Overview")
        st.write(f"**Link:** {st.session_state.active_bid_link if st.session_state.active_bid_link else 'Not Provided'}")
        st.info(st.session_state.summary_ans)

    with t2:
        st.markdown("#### 🛠️ Equipment List")
        st.success(st.session_state.tech_ans)

    with t3:
        st.markdown("#### 📝 Submission Guide")
        st.warning(st.session_state.submission_ans)

    with t4:
        st.markdown("#### ⚖️ Compliance Checklist")
        st.error(st.session_state.compliance_ans)

    with t5:
        st.markdown("#### 💰 Award Info")
        st.write(st.session_state.award_ans)
