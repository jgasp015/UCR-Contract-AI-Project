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

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if not st.session_state.active_bid_text:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:5000]
            st.rerun()

# --- 4. STATUS HEADER & ANALYSIS ---
if st.session_state.active_bid_text:
    
    # Check Status Automatically
    if not st.session_state.status_flag:
        st.session_state.status_flag = query_groq(
            f"Is this bid Awarded, Closed, or Expired? Answer ONLY with the status word or 'Active': {st.session_state.active_bid_text}",
            "Status Auditor."
        )

    # Display Status Banner
    if "Active" not in st.session_state.status_flag:
        st.error(f"🚨 DOCUMENT STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ DOCUMENT STATUS: ACTIVE / OPEN")

    st.divider()
    
    # 5 COLUMNS for complete lifecycle analysis
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("Bid Overview"):
            st.session_state.summary_ans = query_groq(f"Summarize project: {st.session_state.active_bid_text}", "Advisor.")
            st.session_state.total_saved += 10
        if st.session_state.summary_ans:
            with st.container(border=True):
                st.markdown("#### 📖 Overview")
                st.write(st.session_state.summary_ans)

    with col2:
        if st.button("Tech Specs"):
            st.session_state.tech_ans = query_groq(f"List IT hardware/software: {st.session_state.active_bid_text}", "IT Auditor.")
            st.session_state.total_saved += 20
        if st.session_state.tech_ans:
            with st.container(border=True):
                st.markdown("#### 🛠️ Specs")
                st.write(st.session_state.tech_ans)

    with col3:
        if st.button("Submission"):
            st.session_state.submission_ans = query_groq(f"Deadlines and submission: {st.session_state.active_bid_text}", "Advisor.")
            st.session_state.total_saved += 15
        if st.session_state.submission_ans:
            with st.container(border=True):
                st.markdown("#### 📝 Submission")
                st.write(st.session_state.submission_ans)

    with col4:
        if st.button("Compliance"):
            st.session_state.compliance_ans = query_groq(f"Mandatory compliance/reporting: {st.session_state.active_bid_text}", "Auditor.")
            st.session_state.total_saved += 15
        if st.session_state.compliance_ans:
            with st.container(border=True):
                st.markdown("#### ⚖️ Compliance")
                st.write(st.session_state.compliance_ans)

    with col5:
        # NEW: Awarded Vendor & Amount
        if st.button("Award Details"):
            st.session_state.award_ans = query_groq(
                f"Identify the Awarded Vendor and the Contract Amount. If not found, say 'No award info in this document': {st.session_state.active_bid_text}",
                "Financial Auditor."
            )
            st.session_state.total_saved += 20
        if st.session_state.award_ans:
            with st.container(border=True):
                st.markdown("#### 💰 Award Info")
                st.write(st.session_state.award_ans)
