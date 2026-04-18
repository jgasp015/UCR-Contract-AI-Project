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
    """Sends the request to Groq and returns the response plus the time it took."""
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

def scrape_url(url):
    """BeautifulSoup logic to extract text from a live bidding portal."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (UCR Research Project)"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Strip away navigation, scripts, and footers
        for tags in soup(["script", "style", "nav", "footer", "header"]):
            tags.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        return text[:6000] # Limits text to fit within AI context window
    except Exception as e:
        return f"Error scraping URL: {str(e)}"

# --- 3. STREAMLIT UI ---

st.title("🏛️ Public Sector Contract Simplifier")
st.markdown("### Aiming for 90% Data Accuracy & 30% Efficiency Gains")

# Sidebar for Project Theory & Metrics
with st.sidebar:
    st.header("Project Performance")
    st.write("**Theory:** Based on Ladeur (2007) - procedural context in public contracts.")
    
    if 'total_saved' not in st.session_state:
        st.session_state.total_saved = 0
    
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    st.divider()
    st.caption("UCR Master of Science in Engineering - Jeffrey Gaspar")

# --- STEP 1: DATA INPUT ---
# This is the 'Scraping Part' you were looking for!
input_mode = st.radio("Choose Data Source:", ["Live Portal Link (BeautifulSoup)", "Upload PDF"])

raw_contract_text = ""

if input_mode == "Live Portal Link (BeautifulSoup)":
    url_input = st.text_input("Paste the Bidding Portal URL (e.g., City of LA):")
    if url_input:
        with st.spinner("BeautifulSoup is scanning the portal..."):
            raw_contract_text = scrape_url(url_input)
            if "Error" not in raw_contract_text:
                st.success("Web data successfully captured from the portal!")
            else:
                st.error(raw_contract_text)

else:
    uploaded_file = st.file_uploader("Upload a Contract (PDF)", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        # TOKEN LIMIT FIX: Read First, Middle, and Last pages
        pages = [0, len(reader.pages)//2, len(reader.pages)-1] if len(reader.pages) > 2 else range(len(reader.pages))
        raw_contract_text = "".join([reader.pages[i].extract_text() for i in pages])
        st.success(f"PDF processed ({len(reader.pages)} pages detected).")

# --- STEP 2: ANALYSIS ACTIONS ---
if raw_contract_text:
    st.divider()
    st.info("Select an analysis type below to process the captured contract data.")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Simplify for Citizens"):
            role = "You are a plain-language expert. Convert legal jargon into 8th-grade level English."
            prompt = f"Summarize the goal of this bid in 3 simple sentences: {raw_contract_text}"
            with st.spinner("Simplifying..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 📖 Citizen Summary")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Est. Manual Time: 10m")
                    st.session_state.total_saved += 10

    with col2:
        if st.button("Extract Technical Specs"):
            role = "You are a technical procurement expert identifying hardware and software brands."
            prompt = f"List every specific piece of equipment, computer, or software mentioned. Provide a shopping list: {raw_contract_text}"
            with st.spinner("Scanning for Hardware..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 🛠️ Equipment List")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Est. Manual Time: 20m")
                    st.session_state.total_saved += 20

    with col3:
        if st.button("Reporting Guidance"):
            role = "You are a compliance officer. Identify reporting deadlines and procedural vendor obligations."
            prompt = f"Identify every reporting deadline. Tell the vendor exactly what they must submit monthly or quarterly: {raw_contract_text}"
            with st.spinner("Analyzing Deadlines..."):
                ans, dur = query_groq(prompt, role)
                with st.container(border=True):
                    st.markdown("#### 📅 Compliance Checklist")
                    st.write(ans)
                    st.caption(f"AI Speed: {dur}s | Est. Manual Time: 15m")
                    st.session_state.total_saved += 15
