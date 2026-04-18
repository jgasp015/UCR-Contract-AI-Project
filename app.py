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
    """Specific logic for portal tables to find multiple IT bids."""
    it_keywords = ["computer", "software", "network", "telecommunication", "hardware", "radio", "data", "ev ", "cabling", "fiber", "infrastructure"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # LA County & Chicago portals use rows (tr) or specific list items
        rows = soup.find_all(['tr', 'li', 'div', 'span'])
        found_bids = []
        
        for row in rows:
            text = row.get_text(separator=' ', strip=True)
            # Find the link inside this specific row
            link_tag = row.find('a', href=True)
            
            if any(key in text.lower() for key in it_keywords):
                bid_link = urljoin(url, link_tag['href']) if link_tag else url
                # Prevent duplicates and ensure it's a substantial row
                if len(text) > 30 and text[:50] not in [b['name'][:50] for b in found_bids]:
                    found_bids.append({"text": text, "link": bid_link})
        
        return found_bids[:10] # Limit to top 10 for readability
    except Exception as e:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract AI")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Live Portal Link", "Upload PDF"])

if input_mode == "Live Portal Link":
    url_input = st.text_input("Paste Portal URL:")
    if url_input:
        with st.spinner("Searching portal for all IT-related bids..."):
            bids = scrape_multi_it_bids(url_input)
            
            if not bids:
                st.warning("No IT-related bids found on this page.")
            else:
                st.success(f"Found {len(bids)} technology bids!")
                st.divider()
                
                # Custom view for Live Portal (List of all bids)
                for bid in bids:
                    with st.container(border=True):
                        # Use AI to clean up the messy raw row text into a nice Name & Description
                        clean_info = query_groq(
                            f"Extract only the Project Name and a 1-sentence description from this row text: {bid['text']}",
                            "You are a procurement assistant."
                        )
                        st.markdown(f"### 📦 {clean_info}")
                        st.markdown(f"🔗 [View Bid Details]({bid['link']})")
                        st.session_state.total_saved += 5 # 5 mins saved per discovery

else:
    # --- UPLOAD PDF MODE (Remains the same as requested) ---
    uploaded_file = st.file_uploader("Upload PDF", type="pdf")
    manual_url = st.text_input("Paste Source Link for this PDF (Optional):")
    
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        pages = [0, len(reader.pages)-1] if len(reader.pages) > 1 else [0]
        final_text = "".join([reader.pages[i].extract_text() for i in pages])[:4000]
        
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        # Standard buttons for PDF analysis
        with col1:
            if st.button("Bid Overview"):
                ans = query_groq(f"Summarize this project in simple sections (Big Picture, Scope, Who Can Apply): {final_text}", "Professional advisor.")
                with st.container(border=True):
                    st.markdown("#### 📖 Bid Overview")
                    st.write(f"**Link:** {manual_url if manual_url else 'Not Provided'}")
                    st.write(ans)
                    st.session_state.total_saved += 10
        
        with col2:
            if st.button("Technical Specs"):
                ans = query_groq(f"List ONLY the IT hardware/software/cabling: {final_text}", "IT Auditor.")
                with st.container(border=True):
                    st.markdown("#### 🛠️ Equipment List")
                    st.write(ans)
                    st.session_state.total_saved += 20
        # ... (rest of buttons follow the same pattern)
