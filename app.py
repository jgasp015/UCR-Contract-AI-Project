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
    st.error("🔑 API Key missing! Add GROQ_API_KEY to Streamlit Secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    """Universal function to talk to Llama-3.1 via Groq with Rate Limit protection."""
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
        else:
            return f"⚠️ {data.get('error', {}).get('message', 'AI is busy - wait 10 seconds.')}", 0
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}", 0

def scrape_url_with_bid_links(url):
    """Scrapes content and filters specifically for tech keywords and detail links."""
    tech_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev "]
    found_links = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Capture specific BidDetail links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            if "biddetail" in href.lower():
                found_links.append(urljoin(url, href))

        elements = soup.find_all(['span', 'td', 'p', 'li'])
        filtered_text = []
        for el in elements:
            t = el.get_text(strip=True)
            if any(key in t.lower() for key in tech_keywords):
                filtered_text.append(t)
        
        return " | ".join(filtered_text)[:4000], list(set(found_links))
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
        with st.spinner("Scraping and filtering technology data..."):
            final_text, bid_links = scrape_url_with_bid_links(url_input)
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        # Reading cover and end to stay under token limits
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]

if final_text:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Bid Overview"):
            ans, dur = query_groq(f"Summarize this project in simple bullet points: {final_text}", "Clear communication expert.")
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                if bid_links:
                    st.write("🔗 **Detail Links:**")
                    for link in bid_links[:3]: st.markdown(f"[{link}]({link})")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 10

    with col2:
        if st.button("Technical Specs"):
            ans, dur = query_groq(f"List the IT hardware/software items: {final_text}", "IT Auditor.")
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 20

    with col3:
        if st.button("Bid Submission"):
            ans, dur = query_groq(f"List deadlines and how to submit this bid: {final_text}", "Procurement Advisor.")
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 15

    with col4:
        # RENAMED: 'Contract Reporting' is now 'Compliance Requirements'
        if st.button("Compliance Requirements"):
            role = "Senior Compliance and Legal Auditor."
            prompt = (
                f"Identify all mandatory compliance rules, reporting duties, "
                f"and procedural requirements the vendor must follow after winning: {final_text}"
            )
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### ⚖️ Compliance Checklist")
                st.write(ans)
                if "⚠️" not in ans: st.session_state.total_saved += 15
