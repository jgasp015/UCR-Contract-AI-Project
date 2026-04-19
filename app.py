import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# Added 'award_ans' back to the keys
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. HIGH-SPEED AI FUNCTION (Paid Tier Optimized) ---
@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.cache_data.clear()
        for key in ['active_bid_text'] + keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if not st.session_state.active_bid_text:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            # Paid Tier can handle 3 important sections easily
            pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:6000]
            st.rerun()

# --- 4. INSTANT PARALLEL ANALYSIS (5-Tab Logic) ---
if st.session_state.active_bid_text:
    
    if not st.session_state.summary_ans:
        with st.status("⚡ Paid Tier: High-Speed Full Lifecycle Analysis", expanded=True) as status:
            # 1. Status
            st.session_state.status_flag = query_groq_fast(f"Status in 1 word (Active/Awarded/Closed): {st.session_state.active_bid_text}", "Auditor")
            
            # 2. Overview
            st.session_state.summary_ans = query_groq_fast(f"Summarize project scope: {st.session_state.active_bid_text}", "Advisor")
            
            # 3. Tech
            st.session_state.tech_ans = query_groq_fast(f"List ONLY IT hardware/cabling/software: {st.session_state.active_bid_text}", "IT Auditor")
            
            # 4. Submission
            st.session_state.submission_ans = query_groq_fast(f"Identify deadlines and submission steps: {st.session_state.active_bid_text}", "Advisor")
            
            # 5. Compliance (Purely Regulatory)
            st.session_state.compliance_ans = query_groq_fast(f"Identify mandatory compliance, insurance, and reporting rules: {st.session_state.active_bid_text}", "Legal Lead")
            
            # 6. Award & Budget (Purely Financial)
            st.session_state.award_ans = query_groq_fast(f"Extract the Awarded Vendor and total Contract Amount/Budget. If not awarded yet, estimate the budget based on the text: {st.session_state.active_bid_text}", "Financial Auditor")
            
            st.session_state.total_saved += 100 # Increased metric for 5-tab analysis
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    if st.session_state.status_flag and "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    st.divider()
    
    # 5 Separate Tabs
    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award & Budget"])
    
    with t1:
        st.markdown("#### Executive Summary")
        st.info(st.session_state.summary_ans)
    
    with t2:
        st.markdown("#### Technical Requirements")
        st.success(st.session_state.tech_ans)
    
    with t3:
        st.markdown("#### Logistics & Deadlines")
        st.warning(st.session_state.submission_ans)
    
    with t4:
        st.markdown("#### Mandatory Compliance Rules")
        st.error(st.session_state.compliance_ans)
        
    with t5:
        st.markdown("#### Financial Details")
        st.write(st.session_state.award_ans)
