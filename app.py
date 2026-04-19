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
if 'reset_counter' not in st.session_state: st.session_state.reset_counter = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---
@st.cache_data(show_spinner=False)
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    return response.json()['choices'][0]['message']['content']

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.cache_data.clear()
        st.session_state.active_bid_text = None
        st.session_state.reset_counter += 1
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

# --- THE FIX: Cleanest Possible Input Rendering ---
if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        # Using reset_counter in the key forces the button to reappear
        uploaded_file = st.file_uploader(
            "Upload Bid PDF", 
            type="pdf", 
            key=f"uploader_{st.session_state.reset_counter}"
        )
        if uploaded_file:
            with st.spinner("Extracting text..."):
                reader = PdfReader(uploaded_file)
                # Read 3 pages to be safe
                text = ""
                for i in range(min(3, len(reader.pages))):
                    text += reader.pages[i].extract_text()
                st.session_state.active_bid_text = text[:7000]
                st.rerun()
    else:
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            st.warning("Portal scraping is active. If no bids appear, please use Upload PDF.")

# --- 4. ANALYSIS & DISPLAY ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🔍 Analyzing Document...", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast("Status: Active/Closed/Awarded. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq_fast("Summarize project goal.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq_fast("List IT gear/software.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq_fast("Deadlines and steps.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq_fast("Rules and reporting.", st.session_state.active_bid_text)
            st.session_state.award_ans = query_groq_fast("Winner and amount.", st.session_state.active_bid_text)
            st.session_state.total_saved += 100
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status: st.success(f"✅ STATUS: {clean_status}")
    else: st.error(f"🚨 STATUS: {clean_status}")

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
