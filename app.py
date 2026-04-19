import streamlit as st
import requests
from pypdf import PdfReader

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
def query_groq_fast(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI & INPUT ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.session_state.active_bid_text = None
        st.session_state.reset_counter += 1
        for key in keys: st.session_state[key] = None
        st.rerun()

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])

if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.reset_counter}")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            text = ""
            # Read first 3 pages
            for i in range(min(3, len(reader.pages))):
                text += reader.pages[i].extract_text() or ""
            st.session_state.active_bid_text = text[:8000]
            st.rerun()
    else:
        st.text_input("Portal URL (Experimental):", key="url_input")

# --- 4. THE ANALYSIS (STAY ON SCREEN FIX) ---
if st.session_state.active_bid_text:
    # If we haven't analyzed yet, do it now
    if st.session_state.summary_ans is None:
        with st.status("🔍 Analyzing Document...", expanded=True) as status:
            st.session_state.status_flag = query_groq_fast("Status: Active/Closed/Awarded. 1 word.", st.session_state.active_bid_text)
            st.session_state.summary_ans = query_groq_fast("Summarize project goal.", st.session_state.active_bid_text)
            st.session_state.tech_ans = query_groq_fast("List IT gear/software/cabling.", st.session_state.active_bid_text)
            st.session_state.submission_ans = query_groq_fast("Deadlines and steps.", st.session_state.active_bid_text)
            st.session_state.compliance_ans = query_groq_fast("Rules and reporting.", st.session_state.active_bid_text)
            st.session_state.award_ans = query_groq_fast("Winner and amount.", st.session_state.active_bid_text)
            st.session_state.total_saved += 100
            status.update(label="Complete!", state="complete", expanded=False)
            st.rerun()

    # --- THE DISPLAY (WRAPPED IN TRY TO PREVENT DISAPPEARING) ---
    try:
        status_text = str(st.session_state.status_flag).upper()
        if "ACTIVE" in status_text:
            st.success(f"✅ STATUS: {status_text}")
        else:
            st.error(f"🚨 STATUS: {status_text}")

        st.divider()

        # We create the tabs
        t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
        
        # We use st.write() inside each to ensure strings are handled safely
        with t1: st.info(st.session_state.summary_ans)
        with t2: st.success(st.session_state.tech_ans)
        with t3: st.warning(st.session_state.submission_ans)
        with t4: st.error(st.session_state.compliance_ans)
        with t5: st.write(st.session_state.award_ans)
        
    except Exception as e:
        st.warning("Display Error: The AI response contains complex characters. Attempting raw render...")
        st.write(st.session_state.summary_ans)
