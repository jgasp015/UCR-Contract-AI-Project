import streamlit as st
import requests
from pypdf import PdfReader
import io
import time

# --- 1. THE PERMANENT VAULT ---
# We use a very strict check to make sure variables NEVER reset to None.
def init_vault():
    for key in ['active_bid_text', 'agency_name', 'project_title', 'summary_ans', 'tech_ans', 'apply_ans']:
        if key not in st.session_state:
            st.session_state[key] = None

init_vault()

def hard_reset():
    for key in ['agency_name', 'project_title', 'summary_ans', 'tech_ans', 'apply_ans']:
        st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. THE "PLATE-IN-HAND" ENGINE ---
def call_ai(text, prompt):
    """Retries 3 times automatically if the AI 'ghosts' us."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. Use simple words. Mom-test style."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}
        ],
        "temperature": 0.0
    }
    
    for attempt in range(3):
        try:
            time.sleep(1.2) # Essential "cool down" for the API
            r = requests.post(API_URL, headers=headers, json=payload, timeout=25)
            res = r.json()
            if "choices" in res:
                content = res['choices'][0]['message']['content'].strip()
                if len(content) > 5: return content # Confirm we got a real answer
        except:
            continue
    return None

# --- 3. THE INTERFACE ---
if st.session_state.active_bid_text:
    # BACK BUTTON - ALWAYS VISIBLE AT TOP
    if st.button("🏠 Exit Analysis"):
        st.session_state.active_bid_text = None
        hard_reset()
        st.rerun()

    doc = st.session_state.active_bid_text

    # STEP-BY-STEP "NONE" PROTECTION
    if st.session_state.agency_name is None:
        with st.status("🔍 Locating Agency...") as s:
            result = call_ai(doc, "What is the Agency Name?")
            if result: 
                st.session_state.agency_name = result
                st.rerun() # LOCK IT IN
    
    if st.session_state.project_title is None:
        with st.status("📄 Identifying Project...") as s:
            result = call_ai(doc, "What is the Project Title?")
            if result:
                st.session_state.project_title = result
                st.rerun() # LOCK IT IN

    # HEADER DISPLAY (No more "None" because of the logic above)
    st.success("✅ ANALYSIS READY")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID:** {st.session_state.project_title}")

    # TABS (Only triggers AI when the tab is clicked)
    t1, t2, t3 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply"])
    
    with t1:
        if st.session_state.summary_ans is None:
            with st.spinner("Simplifying..."):
                st.session_state.summary_ans = call_ai(doc, "What are the project goals?")
                st.rerun()
        st.info(st.session_state.summary_ans)

    with t2:
        if st.session_state.tech_ans is None:
            with st.spinner("Analyzing Tech..."):
                st.session_state.tech_ans = call_ai(doc, "List the software/hardware tools needed.")
                st.rerun()
        st.success(st.session_state.tech_ans)

else:
    # MAIN MENU
    st.title("🏛️ Public Sector Contract Analyzer")
    t_bid, t_url = st.tabs(["📄 Upload Bid", "🔗 Scan Portal"])
    
    with t_bid:
        up = st.file_uploader("Drop PDF here", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            hard_reset()
            st.rerun()

    with t_url:
        st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        st.button("Scan Portal")
