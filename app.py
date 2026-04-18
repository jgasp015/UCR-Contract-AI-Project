import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

if 'total_saved' not in st.session_state: 
    st.session_state.total_saved = 0

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": system_role}, {"role": "user", "content": prompt}],
        "temperature": 0.0 
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=25)
        data = response.json()
        return data['choices'][0]['message']['content'] if "choices" in data else "⚠️ AI Busy"
    except:
        return "⚠️ Connection Error"

def scrape_multi_it_bids(url):
    it_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev ", "cabling", "fiber", "saas", "cloud"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.find_all(['tr', 'div', 'li'])
        found_bids = []
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            link_tag = row.find('a', href=True)
            if any(key in text.lower() for key in it_keywords) and len(text) > 40:
                bid_link = urljoin(url, link_tag['href']) if link_tag else url
                found_bids.append({"name": text[:80], "full_text": text, "link": bid_link})
        return found_bids[:10]
    except:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""
manual_url = ""

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Searching portal..."):
            bids = scrape_multi_it_bids(url_input)
            if bids:
                for bid in bids:
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        st.markdown(f"🔗 [Direct Link]({bid['link']})")
                        if st.button("Deep Analyze This Bid Row", key=bid['name']):
                            final_text = bid['full_text']
            else:
                st.warning("No IT bids found on that page.")

else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    manual_url = st.text_input("Paste Source Link for this PDF (Optional):")
    if uploaded_file:
        with st.spinner("Reading large PDF..."):
            reader = PdfReader(uploaded_file)
            # Strategy for large 1.7MB PDFs: Read page 1, middle, and end
            pages = [0, len(reader.pages)//2, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
            final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]
            st.success("PDF processed successfully.")

# --- THE 4 BUTTONS (REINSTATED) ---
if final_text:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Bid Overview"):
            ans = query_groq(f"Summarize this project in simple sections (The Big Picture, Technical Scope, Who Can Apply): {final_text}", "Professional advisor.")
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                st.write(f"**Link:** {manual_url if manual_url else 'Not Provided'}")
                st.write(ans)
                st.session_state.total_saved += 10

    with col2:
        if st.button("Technical Specs"):
            ans = query_groq(f"List ONLY the hardware, software, cabling, and infrastructure gear mentioned: {final_text}", "IT Infrastructure Auditor.")
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(ans)
                st.session_state.total_saved += 20

    with col3:
        if st.button("Bid Submission"):
            ans = query_groq(f"What are the deadlines and how do I submit? {final_text}", "Procurement Advisor.")
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(ans)
                st.session_state.total_saved += 15

    with col4:
        if st.button("Compliance Requirements"):
            ans = query_groq(f"Identify all mandatory compliance, insurance, and reporting duties: {final_text}", "Compliance Auditor.")
            with st.container(border=True):
                st.markdown("#### ⚖️ Compliance Checklist")
                st.write(ans)
                st.session_state.total_saved += 15
