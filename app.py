import streamlit as st
import requests
import time
import os
import shutil
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- 1. CONFIG & SETUP ---
# Create a temporary directory for downloads
DOWNLOAD_DIR = os.path.join(os.getcwd(), "temp_downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# --- 2. CORE FUNCTIONS ---

def fetch_document_binary(url):
    """Uses Selenium to click the 'Download' button and capture the file."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Critical: Tell Chrome to download files to our temp folder automatically
    prefs = {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get(url)
        time.sleep(5) # Wait for page
        
        # Look for the 'Download' button seen in your screenshot
        # It's usually a link or button containing the word 'Download'
        try:
            download_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Download')]")
            driver.execute_script("arguments[0].click();", download_btn)
            time.sleep(8) # Wait for download to finish
            
            # Find the file in the directory
            files = os.listdir(DOWNLOAD_DIR)
            if files:
                file_path = os.path.join(DOWNLOAD_DIR, files[0])
                with open(file_path, "rb") as f:
                    data = f.read()
                
                # Cleanup: Remove the file after reading it
                os.remove(file_path)
                return data, files[0]
        except:
            return None, None
    finally:
        driver.quit()

# --- 3. UI INTEGRATION ---

# Inside your ANALYSIS VIEW (Step 4)
if st.session_state.active_bid_text:
    # Rest of your AI tabs...
    
    st.subheader("📄 Bid Documents")
    
    # This checks if we have a URL to try and scrape a document from
    if st.session_state.get('active_bid_url'):
        if st.button("🚀 Pull Document to My Site"):
            with st.spinner("Accessing portal and grabbing file..."):
                file_bytes, file_name = fetch_document_binary(st.session_state.active_bid_url)
                
                if file_bytes:
                    st.success(f"Successfully retrieved: {file_name}")
                    st.download_button(
                        label=f"📥 Download {file_name} from Analyzer",
                        data=file_bytes,
                        file_name=file_name,
                        mime="application/octet-stream"
                    )
                else:
                    st.error("Could not trigger the download. The portal may require a manual login.")
