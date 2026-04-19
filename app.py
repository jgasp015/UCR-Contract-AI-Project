import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Persistent Performance Metrics
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# Storage for AI answers
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CACHED AI FUNCTION (Saves Tokens) ---
@st.cache_data(show_spinner=False)
def query_groq_cached(prompt, system_role):
    """Caches results so you don't waste tokens re-analyzing the same text."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        data = response.json()
        if "choices" in data:
            return data['choices'][0]['message']['content']
        return f"⚠️ Rate Limit: {data.get('error', {}).get('message', 'Busy')}"
    except:
        return "⚠️ Connection Error"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.cache_data.clear() # Clears cache for new file
        for key in ['active_bid_text'] + keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if not st.session_state.active_bid_text:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            # Presentation Strategy: Only read the most important pages (Start & End)
            pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
            # STRICT LIMIT: 3000 chars to stay safe on Free Tier
            st.session_state.active_bid_text = "".join([reader.pages[i].extract_text() for i in pages])[:3000]
            st.rerun()

# --- 4. OPTIMIZED ANALYSIS AREA ---
if st.session_state.active_bid_text:
    
    if not st.session_state.summary_ans:
        with st.status("🚀 Running Presentation-Mode Analysis...", expanded=True) as status:
            st.write("Verifying Status...")
            st.session_state.status_flag = query_groq_cached(f"Status in 1 word (Active/Awarded/Closed): {st.session_state.active_bid_text}", "Auditor")
            time.sleep(3) # Safe delay for Free Tier
            
            st.write("Generating Overview & Tech Specs...")
            st.session_state.summary_ans = query_groq_cached(f"Summarize goal: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.tech_ans = query_groq_cached(f"List IT gear/cabling: {st.session_state.active_bid_text}", "Auditor")
            time.sleep(3)
            
            st.write("Checking Compliance & Awards...")
            st.session_state.submission_ans = query_groq_cached(f"Submission steps: {st.session_state.active_bid_text}", "Advisor")
            st.session_state.compliance_ans = query_groq_cached(f"Compliance & Award info: {st.session_state.active_bid_text}", "Auditor")
            
            st.session_state.total_saved += 80
            status.update(label="Analysis Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    if st.session_state.status_flag and "Active" not in st.session_state.status_flag:
        st.error(f"🚨 STATUS: {st.session_state.status_flag.upper()}")
    else:
        st.success("✅ STATUS: ACTIVE")

    t1, t2, t3, t4 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance & Award"])

    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.write(st.session_state.compliance_ans)
