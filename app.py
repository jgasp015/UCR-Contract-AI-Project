import streamlit as st
import requests
from pypdf import PdfReader

# --- SILO 1: SESSION & STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 360
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

def clear_memory():
    keys = ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 
            'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'bid_details']
    for k in keys: st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- SILO 2: THE "NEVER BLANK" ENGINE ---
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    # Updated instructions: Always give something, never leave it blank.
    system_instruction = """
    You are a helpful assistant. 
    1. If you can't find specific data, summarize what the page is about in 1 simple sentence.
    2. Use the 'Mom-Test': Simple words only.
    3. NO intro text. NO repeating the question.
    4. If the text looks like an empty form, say 'This looks like a blank template'.
    """
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:15000]}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
        content = r.json()['choices'][0]['message']['content'].strip()
        return content if content else "Information not found in this section."
    except:
        return "⚠️ Service busy. Click again."

# --- SILO 3: UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.session_state.active_bid_text:
        if st.button("🏠 Home / Back"):
            st.session_state.active_bid_text = None
            clear_memory()
            st.rerun()

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # 1. HEADER (ALWAYS SHOWS SOMETHING)
    if 'agency_name' not in st.session_state or not st.session_state.agency_name:
        with st.status("🏗️ Reading Document..."):
            st.session_state.agency_name = run_ai(doc, "Which government agency wrote this?")
            st.session_state.project_title = run_ai(doc, "What is the project name or RFP number?")
            st.session_state.detected_due_date = run_ai(doc, "When is the deadline? Give just the date.")
        st.rerun()

    st.success(f"● STATUS: ACTIVE | 📅 DUE: {st.session_state.detected_due_date}")
    st.write(f"**🏛️ WHO:** {st.session_state.agency_name}")
    st.write(f"**📄 WHAT:** {st.session_state.project_title}")
    st.divider()
    
    # 2. TABS
    tabs = st.tabs(["📋 Details", "📖 The Plan", "🛠️ Tools", "⚖️ The Rules"])
    
    with tabs[0]:
        if not st.session_state.get('bid_details'):
            st.session_state.bid_details = run_ai(doc, "Find ID numbers and contact emails.")
        st.write(st.session_state.bid_details)
        
    with tabs[1]:
        if not st.session_state.get('summary_ans'):
            st.session_state.summary_ans = run_ai(doc, "Explain what they want to do in 3 simple points.")
        st.info(st.session_state.summary_ans)

else:
    st.title("🏛️ Reporting Tool")
    up = st.file_uploader("Upload Bid PDF", type="pdf")
    if up:
        text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
        if len(text.strip()) < 50:
            st.error("❌ This PDF looks like a scanned image. I can't read the text. Please upload a 'text-searchable' PDF.")
        else:
            st.session_state.active_bid_text = text
            clear_memory()
            st.rerun()
