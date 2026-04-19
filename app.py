import streamlit as st
import requests
import time
from io import BytesIO
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# --- 1. SESSION STATE INITIALIZATION ---
if 'all_bids' not in st.session_state: st.session_state.all_bids = []
if 'active_bid' not in st.session_state: st.session_state.active_bid = None
if 'total_saved' not in st.session_state: st.session_state.total_saved = 0

def reset_search():
    st.session_state.all_bids = []
    st.session_state.active_bid = None

def go_back():
    st.session_state.active_bid = None

# --- 2. IMPROVED SCRAPER (Finds Documents) ---
def scrape_with_docs(url):
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        found = []
        rows = soup.find_all('tr')
        for row in rows:
            text = row.get_text(strip=True)
            if "RFB" in text or "RFP" in text:
                # Find the document link inside the row
                doc_link = row.find('a', href=lambda x: x and ('.pdf' in x or '.doc' in x))
                full_doc_url = urljoin(url, doc_link['href']) if doc_link else None
                
                found.append({
                    "name": text[:100].upper(),
                    "content": text,
                    "doc_url": full_doc_url
                })
        return found
    except:
        return []

# --- 3. UI LOGIC ---
st.title("🏛️ Public Sector Contract Analyzer")

# Sidebar
with st.sidebar:
    st.metric("Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔍 New Search"): reset_search()

# VIEW 1: Analysis View (If a bid is selected)
if st.session_state.active_bid:
    if st.button("⬅️ Back to Search Result List"): go_back()
    
    bid = st.session_state.active_bid
    st.subheader(f"Analyzing: {bid['name']}")
    
    # DOWNLOAD SECTION
    if bid['doc_url']:
        try:
            # We download the file into memory so the user can grab it from YOUR site
            file_data = requests.get(bid['doc_url']).content
            st.download_button(
                label="📥 Download Original Bid Document",
                data=file_data,
                file_name="bid_document.pdf",
                mime="application/pdf"
            )
        except:
            st.warning("Could not auto-fetch the file. Try clicking the source link.")

    # (Insert your AI Analysis Tabs here as before...)

# VIEW 2: Search Result List (If bids are found but none selected)
elif st.session_state.all_bids:
    st.write(f"Found {len(st.session_state.all_bids)} bid opportunities:")
    for idx, bid in enumerate(st.session_state.all_bids):
        with st.container(border=True):
            st.write(f"**{bid['name']}**")
            if st.button("Analyze & View Details", key=f"analyze_{idx}"):
                st.session_state.active_bid = bid
                st.rerun()

# VIEW 3: Initial Search View
else:
    url_input = st.text_input("Paste Portal URL:")
    if st.button("Scrape Bids"):
        with st.spinner("Finding bids and documents..."):
            st.session_state.all_bids = scrape_with_docs(url_input)
            st.rerun()
