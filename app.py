import streamlit as st
from pypdf import PdfReader
import requests

# --- PROJECT SETUP ---
# Your Groq API Key
GROQ_API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

def query_ai(prompt):
    """Sends the request to the high-speed Groq AI server."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are a technical procurement expert. Your goal is to identify hardware, software brands, and equipment."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        "temperature": 0.1
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        data = response.json()
        if "choices" in data:
            return data['choices'][0]['message']['content']
        return f"⚠️ AI Error: {data.get('error', {}).get('message', 'Unknown error')}"
    except Exception as e:
        return f"⚠️ Connection Error: {str(e)}"

# --- STREAMLIT UI ---
st.set_page_config(page_title="UCR Contract AI", layout="wide")
st.title("🏛️ Public Sector Contract Simplifier")
st.markdown("### Aiming for 90% Data Accuracy & 30% Efficiency Gains")

# STEP 1: Define uploaded_file first
uploaded_file = st.file_uploader("Upload a Contract (PDF)", type="pdf")

# STEP 2: Only then use it in the 'if' statement
if uploaded_file:
    reader = PdfReader(uploaded_file)
    
    # TOKEN LIMIT FIX: Read only page 1 and the last 2 pages
    # This keeps us under the 6,000 token Groq limit
    first_page = list(reader.pages[:1])
    last_pages = list(reader.pages[-2:])
    pages_to_read = first_page + last_pages
    
    raw_text = "".join([p.extract_text() for p in pages_to_read])
    # Final safety cut to avoid 'Request too large' errors
    safe_text = raw_text[:4500] 
    
    st.success("Contract analyzed! Scanning specifically for hardware and reporting tasks...")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Simplify for Citizens"):
            prompt = f"Summarize this bid's goal in 3 simple sentences: {safe_text}"
            st.write(query_ai(prompt))

    with col2:
        if st.button("Extract Technical Specs"):
            st.success("Scanning for Hardware & Software...")
            # Prompting specifically for the Motorola/Printer/Computer list
            prompt = (
                f"List every specific piece of equipment, computer, printer, or software "
                f"mentioned here. Provide a shopping list: {safe_text}"
            )
            st.write(query_ai(prompt))

    with col3:
        if st.button("Reporting Guidance"):
            st.warning("Creating To-Do List...")
            # Actionable 'Every month' guidance
            prompt = (
                f"Identify reporting deadlines. Tell the vendor exactly: "
                f"'Every month you must...' or 'Every quarter you must...': {safe_text}"
            )
            st.write(query_ai(prompt))

st.divider()
st.caption("UCR Master of Science in Engineering Project - Jeffrey Gaspar")