import streamlit as st
import requests
from pypdf import PdfReader
from bs4 import BeautifulSoup
import io
import re

# --- 1. THE VAULT (CACHING) ---
# This tells Streamlit: "Run this once, and save the answer in memory forever."
@st.cache_data(show_spinner=False)
def get_ai_response(text, prompt, system_msg, api_key):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": f"{system_msg} Use simple words for a mother to understand."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:12000]}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"⚠️ Error: {str(e)}. Please click the button again."

# --- 2. SESSION INITIALIZATION ---
if 'pdf_text' not in st.session_state: st.session_state.pdf_text = None
if 'mode' not in st.session_state: st.session_state.mode = "Standard"

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 3. UI FLOW ---
if st.session_state.pdf_text:
    if st.button("🏠 Start New Document"):
        st.session_state.pdf_text = None
        st.cache_data.clear() # Clears the "Vault" for the next file
        st.rerun()

    text = st.session_state.pdf_text

    if st.session_state.mode == "Reporting":
        st.header("📊 Performance & SLA Analysis")
        if st.button("🚀 Analyze Performance"):
            res = get_ai_response(text, "Summarize Uptime, Penalties, and Stop-Clock rules.", "Compliance Expert.", GROQ_API_KEY)
            st.markdown(res)
    else:
        st.header("📄 Bid Document Simplified")
        
        # We process the header first
        if st.button("🔍 Step 1: Identify Bid"):
            header = get_ai_response(text, "What is the Agency, Title, and ID?", "Fact Finder.", GROQ_API_KEY)
            st.success(header)
        
        st.divider()
        
        # TABS - Manual clicks ensure the AI doesn't get overwhelmed
        t1, t2, t3 = st.tabs(["📖 The Plan", "🛠️ The Tech", "📝 How to Apply"])
        
        with t1:
            if st.button("Show Plan"):
                st.info(get_ai_response(text, "What are the goals?", "Mom-test.", GROQ_API_KEY))
        with t2:
            if st.button("Show Tech"):
                st.success(get_ai_response(text, "What software/hardware is needed?", "Tech Expert.", GROQ_API_KEY))
        with t3:
            if st.button("Show Steps"):
                st.warning(get_ai_response(text, "What are the 3 steps to apply?", "Guide.", GROQ_API_KEY))

else:
    # --- MAIN MENU (WORKING URL SCANNER PRESERVED) ---
    st.title("🏛️ Public Sector Contract Analyzer")
    tab_bid, tab_perf, tab_url = st.tabs(["📄 Bid Document", "📊 Performance", "🔗 Agency URL"])
    
    with tab_bid:
        up = st.file_uploader("Upload Bid PDF", type="pdf")
        if up:
            st.session_state.pdf_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.mode = "Standard"
            st.rerun()

    with tab_perf:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf")
        if up_c:
            st.session_state.pdf_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.mode = "Reporting"
            st.rerun()

    with tab_url:
        u_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Scan Portal"):
            # This uses the simple scraper logic which you said works perfectly
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                r = requests.get(u_in, headers=headers, timeout=10)
                soup = BeautifulSoup(r.text, 'html.parser')
                for row in soup.find_all('tr')[:10]: # Just show first few to confirm
                    st.write(row.get_text()[:100] + "...")
            except: st.error("Portal busy.")
