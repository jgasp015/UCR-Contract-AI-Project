import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

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
    st.error("🔑 API Key missing!")
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
st.title("🏛️ Public Sector Contract AI")

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

# --- 4. ANALYSIS AREA (Using st.tabs to stop overlapping) ---
if st.session_state.active_bid_text:
    
    # Auto-check status
    if not st.session_state.status_flag:
        st.session_state.status_flag = query_groq(f"Is this bid Awarded, Closed, or Active? Answer in 1 word: {st.session_state.active_bid_text}", "Auditor.")

    if "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    st.divider()
    
    # NEW: Creating actual Tabs instead of Columns to prevent overlapping
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])

    with t1:
        if st.button("Analyze Overview"):
            st.session_state.summary_ans = query_groq(f"Summarize project scope: {st.session_state.active_bid_text}", "Advisor.")
            st.session_state.total_saved += 10
        if st.session_state.summary_ans:
            st.info(st.session_state.summary_ans)

    with t2:
        if st.button("Analyze Tech Specs"):
            st.session_state.tech_ans = query_groq(f"List ONLY IT hardware/software/cabling: {st.session_state.active_bid_text}", "IT Auditor.")
            st.session_state.total_saved += 20
        if st.session_state.tech_ans:
            st.success(st.session_state.tech_ans)

    with t3:
        if st.button("Analyze Submission"):
            st.session_state.submission_ans = query_groq(f"Deadlines and how to submit: {st.session_state.active_bid_text}", "Advisor.")
            st.session_state.total_saved += 15
        if st.session_state.submission_ans:
            st.warning(st.session_state.submission_ans)

    with t4:
        if st.button("Analyze Compliance"):
            st.session_state.compliance_ans = query_groq(f"Mandatory rules and reporting: {st.session_state.active_bid_text}", "Auditor.")
            st.session_state.total_saved += 15
        if st.session_state.compliance_ans:
            st.error(st.session_state.compliance_ans)

    with t5:
        if st.button("Analyze Award"):
            st.session_state.award_ans = query_groq(f"Identify Awarded Vendor and Amount: {st.session_state.active_bid_text}", "Financial Auditor.")
            st.session_state.total_saved += 20
        if st.session_state.award_ans:
            st.write(st.session_state.award_ans)
