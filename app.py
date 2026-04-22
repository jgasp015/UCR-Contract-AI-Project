import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- SILO 1: SESSION & STATE ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'portal_hits': [], 'agency_name': None, 'project_title': None, 
        'detected_due_date': None, 'summary_ans': None, 'tech_ans': None, 
        'submission_ans': None, 'compliance_ans': None, 'award_ans': None, 
        'bid_details': None, 'report_ans': None, 'total_saved': 360
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved': del st.session_state[key]
    init_state()
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: THE "MOM-TEST" ENGINE ---
def run_ai(text, prompt, persona):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    #persona instructions to be extremely simple and ignore empty templates
    system_instruction = f"""
    You are {persona}. 
    STRICT RULES:
    1. Explain like the user is a total beginner (The Mom-Test).
    2. If a value is missing or looks like a template placeholder (e.g., 'Questions due by: [Date]'), say 'Not listed yet'.
    3. Use short, punchy bullet points.
    4. Use zero professional jargon.
    """
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"{prompt}\n\nDOCUMENT TEXT:\n{text[:12000]}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except:
        return "⚠️ I'm a bit overwhelmed. Try clicking again!"

# --- SILO 3: UI FLOW ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.session_state.active_bid_text:
        if st.button("🏠 Home / Back"):
            hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # 1. HEADER DATA (FORCED MOM-TEST)
    if not st.session_state.agency_name:
        with st.status("🏗️ Reading the basics..."):
            st.session_state.agency_name = run_ai(doc, "Who is the Government Agency? (Name only)", "a helpful assistant")
            st.session_state.project_title = run_ai(doc, "What is the specific Title/RFP number? (Short)", "a helpful assistant")
            st.session_state.detected_due_date = run_ai(doc, "What is the exact deadline date? If not found, say Not specified.", "a helpful assistant")
        st.rerun()

    st.success(f"● STATUS: ACTIVE | 📅 DEADLINE: {st.session_state.detected_due_date}")
    st.write(f"**🏛️ WHO:** {st.session_state.agency_name}")
    st.write(f"**📄 WHAT:** {st.session_state.project_title}")
    st.divider()
    
    # 2. TABS (THE SIMPLE VERSION)
    if st.session_state.analysis_mode == "Reporting":
        # (Reporting logic stays here)
        pass
    else:
        if not st.session_state.summary_ans:
            with st.status("🚀 Making it simple..."):
                st.session_state.bid_details = run_ai(doc, "Find the ID number and the contact email. Format as simple list.", "a secretary")
                st.session_state.summary_ans = run_ai(doc, "In 3 bullet points, what do they want to buy? Explain like a grocery list.", "a translator")
                st.session_state.tech_ans = run_ai(doc, "What computers or software are mentioned? List them simply.", "a tech teacher")
                st.session_state.submission_ans = run_ai(doc, "Give me 3 easy steps to apply. Use 1, 2, 3.", "a coach")
                st.session_state.compliance_ans = run_ai(doc, "What are the rules or insurance? (Explain simply)", "a lawyer for beginners")
                st.session_state.award_ans = run_ai(doc, "How do they choose the winner? (Simple words)", "a fair judge")
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 The Plan", "🛠️ Tools", "📝 How to Apply", "⚖️ The Rules", "💰 How to Win"])
        tabs[0].markdown(st.session_state.bid_details)
        tabs[1].info(st.session_state.summary_ans)
        tabs[2].success(st.session_state.tech_ans)
        tabs[3].warning(st.session_state.submission_ans)
        tabs[4].error(st.session_state.compliance_ans)
        tabs[5].write(st.session_state.award_ans)

else:
    # MAIN MENU (Clean & Empty URL)
    st.title("🏛️ Reporting Tool")
    t1, t2, t3 = st.tabs(["📄 New Bid", "📊 Check Performance", "🔗 Scan Portal"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; st.rerun()
    # (Rest of menu logic...)
