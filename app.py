import streamlit as st
import requests
from pypdf import PdfReader
import io
import time

# --- SILO 1: RECOVERY-FIRST STATE ---
# This ensures that even if the app "blips," it remembers what it already found.
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'agency_name': None, 'project_title': None, 'detected_due_date': None,
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None, 'report_ans': None
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def reset_analysis():
    for k in ['agency_name', 'project_title', 'detected_due_date', 'summary_ans', 'tech_ans', 
                'submission_ans', 'compliance_ans', 'award_ans', 'bid_details', 'report_ans']:
        st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: THE "SLOW & STEADY" ENGINE ---
def run_ai(text, prompt, system_msg):
    # THE FIX: We wait 1.5 seconds between requests to ensure the AI doesn't block us
    time.sleep(1.5) 
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": f"{system_msg} Use the Mom-Test: Simple words only."}, 
                     {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = r.json()
        if "choices" in res:
            return res['choices'][0]['message']['content'].strip()
        return None
    except:
        return None

# --- SILO 3: UI FLOW (THE "STEP-BY-STEP" LOADER) ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()
    
    doc = st.session_state.active_bid_text

    # STEP 1: GET THE HEADER (ONLY IF WE DON'T HAVE IT)
    if not st.session_state.agency_name:
        with st.status("🏗️ Identifying Agency...") as s:
            ans = run_ai(doc, "What is the Agency Name?", "Name only.")
            if ans: 
                st.session_state.agency_name = ans
                st.rerun() # Refresh to show the result and move to next step

    if not st.session_state.project_title:
        with st.status("📄 Identifying Project...") as s:
            ans = run_ai(doc, "What is the Project Name?", "Name only.")
            if ans: 
                st.session_state.project_title = ans
                st.rerun()

    # DISPLAY WHAT WE HAVE SO FAR
    st.success(f"● BID LOADED")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

    # STEP 2: LOAD TABS ONE BY ONE
    tabs = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal"])
    
    with tabs[0]: # Plan Tab
        if not st.session_state.summary_ans:
            with st.spinner("Writing Plan..."):
                ans = run_ai(doc, "What are the goals? (Simple words)", "Mom-test.")
                if ans: st.session_state.summary_ans = ans; st.rerun()
        st.info(st.session_state.summary_ans)

    with tabs[1]: # Tech Tab
        if not st.session_state.tech_ans:
            with st.spinner("Listing Tech..."):
                ans = run_ai(doc, "What software/hardware is needed? Max 5.", "List items.")
                if ans: st.session_state.tech_ans = ans; st.rerun()
        st.success(st.session_state.tech_ans)

else:
    # --- MAIN MENU (STAYS UNTOUCHED) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; reset_analysis(); st.rerun()
    # (Rest of menu logic remains identically protected)
