import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    start_time = time.time()
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
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        data = response.json()
        duration = round(time.time() - start_time, 2)
        if "choices" in data:
            return data['choices'][0]['message']['content'], duration
        return f"⚠️ API Error: {data.get('error', {}).get('message', 'Unknown')}", 0
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}", 0

def scrape_url_with_broad_tech_filter(url):
    tech_keywords = [
        "computer", "laptop", "server", "software", "database", "cloud", "data", "storage",
        "network", "telecommunication", "broadband", "wi-fi", "ethernet", "radio", "voip", "cabling", "fiber",
        "hardware", "printer", "scanner", "copier", "peripheral", "monitor",
        "electric vehicle", "ev charging", "smart city", "iot", "security", "cyber", "electronic"
    ]
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        elements = soup.find_all(['span', 'a', 'td', 'p', 'li', 'h3'])
        filtered_results = []
        for el in elements:
            text = el.get_text(strip=True)
            if any(key in text.lower() for key in tech_keywords):
                if text not in filtered_results and len(text) > 5:
                    filtered_results.append(text)
        return " | ".join(filtered_results)[:7000] if filtered_results else "No relevant Tech/IT content found."
    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")
st.markdown("### Efficiency Analysis & Procedural Transparency")

with st.sidebar:
    st.header("Project Performance")
    if 'total_saved' not in st.session_state: 
        st.session_state.total_saved = 0
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    
    if 'current_url' in st.session_state and st.session_state.current_url:
        st.divider()
        st.write("🔗 **Quick Link:**")
        st.link_button("View Original Portal", st.session_state.current_url)
        
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        st.session_state.current_url = url_input
        with st.spinner("Scraping..."):
            final_text = scrape_url_with_broad_tech_filter(url_input)
            st.success("Technology context captured!")
else:
    st.session_state.current_url = None
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages_to_read = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
        final_text = "".join([reader.pages[i].extract_text() for i in pages_to_read])
        st.success("PDF analyzed.")

if final_text and "Error" not in final_text:
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Bid Overview"):
            role = "You are a professional who explains things using very simple, basic English for the general public."
            # INSTRUCTION: Super straightforward, short words, simple bullets
            prompt = (
                f"Describe exactly what this bid is for using the simplest words possible. "
                f"Use short sentences. Use bullet points. "
                f"Explain it like you are talking to someone with no technical or legal training: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                # NEW: Link displayed inside the card
                if st.session_state.current_url:
                    st.link_button("🔗 Open Original Bid Link", st.session_state.current_url)
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 10m")
                if "⚠️" not in ans: st.session_state.total_saved += 10

    with col2:
        if st.button("Technical Specs"):
            role = "You are a senior IT & Infrastructure Auditor."
            prompt = f"Extract a list of all technical equipment (Computers, EVs, Networking, Software). Ignore non-tech items: {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 20m")
                if "⚠️" not in ans: st.session_state.total_saved += 20

    with col3:
        if st.button("Bid Submission"):
            role = "Procurement Advisor."
            prompt = f"Identify the specific deadlines and requirements to SUBMIT this bid (dates, portals, required forms): {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 15m")
                if "⚠️" not in ans: st.session_state.total_saved += 15

    with col4:
        if st.button("Contract Reporting"):
            role = "Contract Compliance Manager."
            prompt = f"Identify ONGOING reporting requirements AFTER award (monthly reports, quarterly updates, etc.): {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📅 Ongoing Reporting")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 15m")
                if "⚠️" not in ans: st.session_state.total_saved += 15
