import streamlit as st
import requests
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    # Increased timeout for large document processing
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return response.json()['choices'][0]['message']['content']

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.session_state.active_bid_text = None
        st.session_state.uploader_key += 1
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])

if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.uploader_key}")
        if uploaded_file:
            with st.spinner("Processing ENTIRE document... please wait."):
                reader = PdfReader(uploaded_file)
                # CRITICAL CHANGE: Read EVERY page in the document
                full_text = ""
                for page in reader.pages:
                    full_text += page.extract_text() + "\n"
                
                # We send up to 30,000 characters (approx 50 pages of text)
                st.session_state.active_bid_text = full_text[:30000]
                st.rerun()

# --- 4. ANALYSIS ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🔍 Deep-Scanning All Pages...", expanded=True) as status:
            # We use more descriptive prompts to ensure it finds the 'Nlyte' type details
            st.session_state.status_flag = query_groq_fast("Identify bid status. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq_fast("What is the project goal? Look for software maintenance or service descriptions.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq_fast("List all IT items, software modules, and part numbers found in the Price Sheets or Commodity lines.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq_fast("Identify bid due dates and VSS submission steps.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq_fast("Identify insurance and mandatory legal rules.", st.session_state.active_bid_text)
            st.session_state.award_ans = query_groq_fast("Identify the total estimated budget or commodity quantities.", st.session_state.active_bid_text)
            st.session_state.total_saved += 120 
            status.update(label="Deep Analysis Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    clean_status = st.session_state.status_flag.strip().replace(".", "").upper()
    if "ACTIVE" in clean_status: st.success(f"✅ STATUS: {clean_status}")
    else: st.error(f"🚨 STATUS: {clean_status}")

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
