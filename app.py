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

def scrape_url_with_bid_links(url):
    """Scrapes content and specifically looks for direct 'BidDetail' links."""
    tech_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev "]
    found_links = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for links that lead to BidDetail
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True).lower()
            # If the link text is a tech keyword OR the link itself looks like a Detail page
            if any(key in text for key in tech_keywords) or "biddetail" in href.lower():
                full_url = urljoin(url, href)
                if full_url not in found_links:
                    found_links.append(full_url)

        # Standard text scraping for the AI context
        elements = soup.find_all(['span', 'td', 'p', 'li'])
        filtered_text = []
        for el in elements:
            t = el.get_text(strip=True)
            if any(key in t.lower() for key in tech_keywords):
                filtered_text.append(t)
        
        return " | ".join(filtered_text)[:7000], found_links
    except Exception as e:
        return f"Error: {str(e)}", []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")
st.markdown("### Efficiency Analysis & Procedural Transparency")

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
        with st.spinner("Scraping portal and finding direct bid links..."):
            final_text, bid_links = scrape_url_with_bid_links(url_input)
            st.success(f"Captured {len(bid_links)} specific bid links!")
else:
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages = [0, 1, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
        final_text = "".join([reader.pages[i].extract_text() for i in pages])
        st.success("PDF analyzed.")

if final_text and "Error" not in final_text:
    st.divider()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("Bid Overview"):
            role = "You are a professional who uses simple, basic English for the general public."
            prompt = f"Explain what these bids are for in very simple terms using bullet points: {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📖 Bid Overview")
                
                # NEW: Display the specific links found in the scrape
                if bid_links:
                    st.write("🔗 **Direct Bid Detail Links Found:**")
                    for link in bid_links[:5]: # Show top 5 to keep it clean
                        st.markdown(f"[{link}]({link})")
                
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 10m")
                st.session_state.total_saved += 10

    with col2:
        if st.button("Technical Specs"):
            role = "Hardware Auditor."
            prompt = f"List the IT and technical equipment mentioned: {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 🛠️ Equipment List")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 20m")
                st.session_state.total_saved += 20

    with col3:
        if st.button("Bid Submission"):
            role = "Procurement Advisor."
            prompt = f"Identify deadlines and requirements to SUBMIT: {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📝 Submission Guide")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 15m")
                st.session_state.total_saved += 15

    with col4:
        if st.button("Contract Reporting"):
            role = "Compliance Manager."
            prompt = f"Identify ongoing monthly/quarterly reporting requirements: {final_text}"
            ans, dur = query_groq(prompt, role)
            with st.container(border=True):
                st.markdown("#### 📅 Ongoing Reporting")
                st.write(ans)
                st.caption(f"Speed: {dur}s | Saved: 15m")
                st.session_state.total_saved += 15
