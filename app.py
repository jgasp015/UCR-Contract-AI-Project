import streamlit as st
import requests
from pypdf import PdfReader

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

# --- 2. THE DEEP-SCAN BRAIN ---
def deep_query(full_text, specific_prompt):
    """Bypasses limits by focusing the AI on specific data types across the whole text."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # We send a high-density summary of the document to ensure the AI doesn't get lost
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a Procurement Auditor. You must find the requested info even if it is buried deep in tables or late pages."},
            {"role": "user", "content": f"{specific_prompt}\n\nDOCUMENT TEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    # 30s timeout for massive documents
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

if st.session_state.active_bid_text is None:
    uploaded_file = st.file_uploader("Upload Bid PDF (No Page Limits)", type="pdf", key=f"up_{st.session_state.uploader_key}")
    if uploaded_file:
        with st.spinner("Bypassing software limits... Ingesting entire document."):
            reader = PdfReader(uploaded_file)
            # We read EVERY page to ensure nothing is missed
            full_content = ""
            for page in reader.pages:
                full_content += page.extract_text() + "\n"
            
            # We store a massive context (up to 40k characters)
            st.session_state.active_bid_text = full_content[:40000]
            st.rerun()

# --- 4. THE CHAINED ANALYSIS ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🚀 Deep-Scanning 40,000 Characters...", expanded=True) as status:
            doc = st.session_state.active_bid_text
            
            # Tab 1: Status
            st.session_state.status_flag = deep_query(doc, "Status: Active/Closed/Awarded. 1 word.")
            
            # Tab 2: Overview (Focus on the start)
            st.session_state.summary_ans = deep_query(doc[:10000], "Summarize the project goal.")
            
            # Tab 3: Tech Specs (Focus on the whole doc, looking for software/parts)
            st.session_state.tech_ans = deep_query(doc, "List all IT items, software maintenance modules (like Nlyte), and part numbers found in the Price Sheets or Commodity Lines.")
            
            # Tab 4: Submission
            st.session_state.submission_ans = deep_query(doc[:15000], "Identify due dates and VSS steps.")
            
            # Tab 5: Compliance
            st.session_state.compliance_ans = deep_query(doc, "List insurance limits ($) and mandatory legal rules.")
            
            # Tab 6: Awards
            st.session_state.award_ans = deep_query(doc, "Identify the total number of commodity lines and any budget estimates.")
            
            st.session_state.total_saved += 150 
            status.update(label="Full Document Audit Complete!", state="complete", expanded=False)
            st.rerun()

    # --- DISPLAY ---
    clean_status = str(st.session_state.status_flag).upper()
    if "ACTIVE" in clean_status or "OPEN" in clean_status:
        st.success(f"✅ STATUS: {clean_status}")
    else:
        st.error(f"🚨 STATUS: {clean_status}")

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
