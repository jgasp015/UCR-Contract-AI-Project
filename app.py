import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from urllib.parse import urljoin

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing!")
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
        return f"⚠️ {data.get('error', {}).get('message', 'AI busy')}", 0
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}", 0

def scrape_url_with_bid_links(url):
    # Expanded keywords to ensure Cabling and Infrastructure are captured
    tech_keywords = [
        "computer", "software", "network", "telecommunication", "hardware", 
        "radio", "data", "ev ", "cabling", "fiber", "infrastructure", "wireless"
    ]
    found_links = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if "biddetail" in href.lower():
                found_links.append(urljoin(url, href))
        elements = soup.find_all(['span', 'td', 'p', 'li', 'div'])
        filtered_text = " ".join([el.get_text(strip=True) for el in elements if any(key in el.get_text().lower() for key in tech_keywords)])
        return filtered_text[:4000], list(set(found_links))
    except Exception as e:
        return f"Error: {str(e)}", []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

final_text = ""
bid_links = []

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Analyzing..."):
            final_text, bid_links = scrape_url_with_bid_links(url_input)
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]

if final_text:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Bid Overview"):
            role = "You are a professional advisor who simplifies technical government bids."
            # INSTRUCTION: Added focus on 'Improvement' and 'Connectivity'
            prompt = (
                f"Explain this project simply. Follow this structure:\n"
                f"1. **The Big Picture**: Start with 'This bid is about...' "
                f"Explain how this project will improve city infrastructure or connectivity (e.g., faster data, better communication).\n"
                f"2. **What is Needed**: Describe the technical services like cabling, telecommunications, or networking equipment.\n"
                f"3. **Who Can Apply**: Requirements for the vendor (experience with similar city projects, certifications).\n"
                f"Text: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                if bid_links:
                    for link in bid_links[:2]: st.markdown(f"🔗 [Direct Bid Link]({link})")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 10

    with col2:
        if st.button("Technical Specs"):
            # INSTRUCTION: Explicitly include Cabling and Telecomm
            role = "You are a strict technical infrastructure auditor."
            prompt = (
                f"Identify only the IT hardware, software, and physical infrastructuregear EXPLICITLY mentioned. "
                f"Include: Cabling (Cat6, Fiber), Telecommunications systems, Networking hardware, and Data systems. "
                f"STRICTLY DO NOT suggest items. Text: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 20

    with col3:
        if st.button("Bid Submission"):
            ans, dur = query_groq(f"List deadlines and how to submit: {final_text}", "Procurement Advisor.")
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 15

    with col4:
        if st.button("Compliance Requirements"):
            ans, dur = query_groq(f"Identify all mandatory compliance, insurance, and reporting rules: {final_text}", "Legal Compliance Auditor.")
            with st.container(border=True):
                st.markdown("#### ⚖️ Compliance Checklist")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 15
