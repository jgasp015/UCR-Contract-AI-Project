import streamlit as st
import requests
import time
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO

# --- 1. CONFIGURATION & SECRETS ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 API Key missing in Streamlit Secrets! Please add GROQ_API_KEY to your secrets.")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def query_groq(prompt, system_role):
    """Sends the filtered data to Groq and tracks processing speed."""
    start_time = time.time()
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()
        duration = round(time.time() - start_time, 2)
        if "choices" in data:
            return data['choices'][0]['message']['content'], duration
        return "⚠️ AI Error: Could not process request.", duration
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}", 0

def scrape_url_with_it_filter(url):
    """
    Scrapes the portal but ONLY keeps text related to IT keywords.
    This fulfills the 'Data Accuracy' goal of the project.
    """
    it_keywords = [
        "computer", "laptop", "server", "software", "printer", "tablet",
        "network", "internet", "telecommunication", "hardware", "wi-fi",
        "ethernet", "cloud", "database", "security", "voip", "cabling"
    ]
    try:
        headers = {"User-Agent": "Mozilla/5.0 (UCR Research Project)"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Look for text in paragraphs, lists, and tables
        blocks = soup.find_all(['p', 'li', 'td', 'h2', 'h3'])
        
        filtered_results = []
        for block in blocks:
            text = block.get_text(strip=True)
            # Only keep the block if it contains an IT keyword
            if any(key in text.lower() for key in it_keywords):
                filtered_results.append(text)
        
        if not filtered_results:
            return "No IT-related requirements found at this URL. Please try an SOW-specific link."
            
        return " ".join(filtered_results)[:6000] 
    except Exception as e:
        return f"Error scraping URL: {str(e)}"

# --- 3. STREAMLIT UI ---

st.title("🏛️ Public Sector Contract Simplifier")
st.markdown("### Aiming for 90% Data Accuracy & 30% Efficiency Gains")

# Sidebar for Metrics (Project requirement: Assess time saved)
with st.sidebar:
    st.header("Project Performance")
    st.write("**Thesis Context:** Ladeur (2007) - Extracting procedural context from administrative law.")
    
    if 'total_saved' not in st.session_state:
        st.session_state.total_saved = 0
    
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

# --- STEP 1: DATA INPUT (THE SCRAPER) ---
input_mode = st.radio("Choose Data Source:", ["Live Portal Link (IT-Filtered Scrape)", "Upload PDF"])

final_text = ""

if input_mode == "Live Portal Link (IT-Filtered Scrape)":
    url_input = st.text_input("Paste the Bidding Portal URL:")
    if url_input:
        with st.spinner("BeautifulSoup is filtering for IT keywords..."):
            final_text = scrape_url_with_it_filter(url_input)
            if "Error" not in final_text and "No IT-related" not in final_text:
                st.success("Targeted IT data successfully captured!")
            elif "No IT-related" in final_text:
                st.warning(final_text)
            else:
                st.error(final_text)

else:
    uploaded_file = st.file_uploader("Upload a Contract (PDF)", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        # Optimized for SOWs: First, Middle, and Last pages
        pages = [0, len(reader.pages)//2, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
        final_text = "".join([reader.pages[i].extract_text() for i in pages])
        st.success(f"PDF processed ({len(reader.pages)} pages).")

# --- STEP 2: ANALYSIS ACTIONS ---
if final_text and "Error" not in final_text:
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Simplify for Citizens"):
            role = "You are a plain-language advocate."
            prompt = f"Explain what IT services or hardware this bid is asking for in 3 bullet points: {final_text}"
            with st.spinner("Simplifying..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 📖 Citizen Summary")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Saved: 10m")
                    st.session_state.total_saved += 10

    with col2:
        if st.button("Extract Technical Specs"):
            role = "You are a technical procurement expert."
            prompt = f"List every computer, printer, brand, or piece of software mentioned as a shopping list: {final_text}"
            with st.spinner("Scanning Hardware..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 🛠️ Equipment List")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Saved: 20m")
                    st.session_state.total_saved += 20

    with col3:
        if st.button("Reporting Guidance"):
            role = "You are a compliance officer."
            prompt = f"Find the IT reporting deadlines. Tell the vendor exactly what they must submit and when: {final_text}"
            with st.spinner("Analyzing Deadlines..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 📅 Compliance Checklist")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Saved: 15m")
                    st.session_state.total_saved += 15
