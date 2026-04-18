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
    """Deep scraper designed to find IT bids in complex tables."""
    # Expanded keywords for all IT domains
    it_keywords = [
        "computer", "software", "network", "telecommunication", "hardware", 
        "radio", "data", "ev ", "cabling", "fiber", "infrastructure", 
        "saas", "cloud", "maintenance", "digital", "technology"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Target the rows (tr) or cells (td) where the data actually lives
        rows = soup.find_all(['tr', 'div', 'li'])
        found_bids = []
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            # Find the link to the detail page
            link_tag = row.find('a', href=True)
            
            # Check if any IT keyword is in the text
            if any(key in text.lower() for key in it_keywords):
                bid_link = urljoin(url, link_tag['href']) if link_tag else url
                
                # Filter out small menu items or duplicate navigation links
                if len(text) > 40:
                    # Clean the text slightly for the list view
                    clean_name = text[:100] + "..." if len(text) > 100 else text
                    if clean_name not in [b['name'] for b in found_bids]:
                        found_bids.append({"name": clean_name, "full_text": text, "link": bid_link})
        
        return found_bids[:15] # Return more results
    except Exception as e:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Deep scanning portal for technology bids..."):
            bids = scrape_multi_it_bids(url_input)
            
            if not bids:
                st.warning("No IT-related bids found. The portal might be blocking the scraper or using a dynamic script.")
                st.info("Tip: Try pasting the URL for a specific bid page instead of the main list.")
            else:
                st.success(f"Found {len(bids)} possible Technology Bids!")
                st.divider()
                
                # Display results as a clean list of summaries
                for bid in bids:
                    with st.container(border=True):
                        st.markdown(f"### 📦 {bid['name']}")
                        # AI summarizes the specific row for clarity
                        summary = query_groq(
                            f"Summarize what this bid is for in 1 very simple sentence: {bid['full_text']}",
                            "Procurement assistant."
                        )
                        st.write(summary)
                        st.markdown(f"🔗 [Open Original Bid Detail Page]({bid['link']})")
                        if st.button(f"Analyze this Bid", key=bid['name']):
                             st.session_state.total_saved += 5 # Reward discovery

else:
    # PDF MODE REMAINS UNCHANGED
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    manual_url = st.text_input("Paste Source Link for this PDF (Optional):")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]
        
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("Bid Overview"):
                ans = query_groq(f"Summarize this project in 3 simple sections (The Big Picture, Technical Scope, Who Can Apply): {final_text}", "Professional advisor.")
                with st.container(border=True):
                    st.markdown("#### 📖 Bid Overview")
                    st.write(f"**Link:** {manual_url if manual_url else 'Not Provided'}")
                    st.write(ans)
                    st.session_state.total_saved += 10
        # (rest of your technical spec, submission, and compliance buttons go here)
