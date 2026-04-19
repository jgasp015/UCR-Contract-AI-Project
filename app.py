import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

# Initialize Session States
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# Back to 4 standard response keys for maximum stability
keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

# Use your secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing in Secrets!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE CORE AI FUNCTION ---
def query_groq(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
        return response.json()['choices'][0]['message']['content']
    except:
        return "⚠️ Error in analysis. Please try again."

# --- 3. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.session_state.active_bid_text = None
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- DATA INPUT ---
if st.session_state.active_bid_text is None:
    input_mode = st.radio("Select Input:", ["Upload PDF", "Live Portal Link"])
    
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid Document", type="pdf")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            # Read first few pages for the analysis
            extracted = ""
            for i in range(min(4, len(reader.pages))):
                extracted += reader.pages[i].extract_text()
            st.session_state.active_bid_text = extracted[:8000]
            st.rerun()
    else:
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            st.info("Scanning portal... (If this fails, please use Upload PDF)")
            # Basic scraper fallback
            try:
                res = requests.get(url_input, timeout=10)
                st.session_state.active_bid_text = res.text[:8000]
                st.rerun()
            except:
                st.warning("Portal blocked automated access. Please download the bid and use Upload PDF.")

# --- 4. ANALYSIS & TABS ---
if st.session_state.active_bid_text:
    if st.session_state.summary_ans is None:
        with st.status("🔍 Analyzing Contract...", expanded=True) as status:
            st.session_state.status_flag = query_groq("Status: Active/Closed/Awarded. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq("Summarize goal and scope.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq("List IT hardware/software/cabling.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq("List deadlines and submission steps.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq("Identify mandatory rules and budget info.", st.session_state.active_bid_text)
            
            st.session_state.total_saved += 80
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    # Display Result
    st.success(f"✅ STATUS: {st.session_state.status_flag.upper()}")
    st.divider()

    t1, t2, t3, t4 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance & Award"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.write(st.session_state.compliance_ans)
