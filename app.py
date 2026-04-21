import streamlit as st
import requests
import time
from pypdf import PdfReader

# --- SIDEBAR & STATE ---
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None

# Pulls key privately from Secrets (Safe from GitHub alerts!)
if "GROQ_API_KEY" not in st.secrets:
    st.error("🔑 Key missing! Add it to Streamlit Settings > Secrets.")
    st.stop()

GROQ_KEY = st.secrets["GROQ_API_KEY"]

def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "Government Data Extractor. Concise. Simple words."},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text[:10000]}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20)
        return r.json()['choices'][0]['message']['content'].strip()
    except: return None

# --- UI FLOW ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home"):
        st.session_state.active_bid_text = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # Fast Analysis
    st.write("### 📄 Document Analysis")
    if st.button("🔍 Simplify This Bid"):
        with st.status("Reading..."):
            summary = run_ai(doc, "What is the goal and the agency?")
            tech = run_ai(doc, "What tech is needed?")
            apply = run_ai(doc, "How do I apply?")
        
        st.info(f"**Goal:** {summary}")
        st.success(f"**Tech:** {tech}")
        st.warning(f"**Apply:** {apply}")
        st.session_state.total_saved += 120
else:
    up = st.file_uploader("Upload Bid PDF", type="pdf")
    if up:
        st.session_state.active_bid_text = "\n".join([p.extract_text() for p in PdfReader(up).pages])
        st.rerun()
