import streamlit as st
import requests
from pypdf import PdfReader
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="UCR Contract Analyzer", layout="wide")

if 'total_saved' not in st.session_state: st.session_state.total_saved = 0
if 'active_bid_text' not in st.session_state: st.session_state.active_bid_text = None
if 'uploader_key' not in st.session_state: st.session_state.uploader_key = 0

keys = ['summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 'award_ans', 'status_flag']
for key in keys:
    if key not in st.session_state: st.session_state[key] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. CORE FUNCTIONS ---

def deep_query(full_text, specific_prompt, max_tokens=None):
    """High-context AI query. Forces short answers for status."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a concise procurement expert. Provide direct answers without conversational filler."},
            {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{full_text}"}
        ],
        "temperature": 0.0 
    }
    if max_tokens: payload["max_tokens"] = max_tokens
    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    return response.json()['choices'][0]['message']['content']

def scrape_stable_bids(url):
    it_keywords = ["software", "hardware", "network", "cabling", "saas", "cloud", "it ", "technology"]
    junk_words = ["javascript", "detached", "loading", "page 1 of", "items per page"]
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        found_bids = []
        for row in soup.find_all(['tr', 'div']):
            text = row.get_text(separator=' ', strip=True)
            if len(text) > 55 and any(k in text.lower() for k in it_keywords) and not any(j in text.lower() for j in junk_words):
                clean_name = " ".join(text.split())[:115].upper()
                link_tag = row.find('a', href=True)
                bid_link = urljoin(url, link_tag['href']) if link_tag else url
                if clean_name[:60] not in [b['name'][:60] for b in found_bids]:
                    found_bids.append({"name": clean_name, "full_text": text, "link": bid_link})
        return found_bids[:10]
    except:
        return []

# --- 3. UI ---
st.title("🏛️ Public Sector Contract Analyzer")

with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🔄 Start New Search"):
        st.session_state.active_bid_text = None
        st.session_state.uploader_key += 1
        for key in keys: st.session_state[key] = None
        st.rerun()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

input_mode = st.radio("Data Source:", ["Upload PDF", "Live Portal Link"])

if st.session_state.active_bid_text is None:
    if input_mode == "Upload PDF":
        uploaded_file = st.file_uploader("Upload Bid PDF", type="pdf", key=f"up_{st.session_state.uploader_key}")
        if uploaded_file:
            reader = PdfReader(uploaded_file)
            full_content = ""
            for page in reader.pages:
                full_content += page.extract_text() + "\n"
            st.session_state.active_bid_text = full_content[:45000] 
            st.rerun()
    else:
        url_input = st.text_input("Paste Portal URL:")
        if url_input:
            bids = scrape_stable_bids(url_input)
            if bids:
                for idx, bid in enumerate(bids):
                    with st.container(border=True):
                        st.write(f"### 📦 {bid['name']}")
                        if st.button(f"Analyze This Bid", key=f"btn_{idx}"):
                            st.session_state.active_bid_text = bid['full_text']
                            st.rerun()

# --- 4. ANALYSIS ---
if st.session_state.active_bid_text:
    if not st.session_state.summary_ans:
        with st.status("🚀 Chained Deep-Scan in Progress...", expanded=True) as status:
            doc = st.session_state.active_bid_text
            
            # FORCED ONE-WORD STATUS
            st.session_state.status_flag = deep_query(doc, "Identify if this bid is OPEN, ACTIVE, CLOSED, or AWARDED. Answer with ONLY the word.", max_tokens=5)
            
            st.session_state.summary_ans = deep_query(doc, "Summarize project goal and scope.")
            st.session_state.tech_ans = deep_query(doc, "List all IT hardware, software (like Nlyte), and cabling requirements.")
            st.session_state.submission_ans = deep_query(doc, "Identify bid due dates and submission steps.")
            st.session_state.compliance_ans = deep_query(doc, "Identify mandatory insurance and legal rules.")
            st.session_state.award_ans = query_groq_fast("Identify awarded vendor or estimate budget.", doc) # Helper call
            
            st.session_state.total_saved += 150 
            status.update(label="Full Audit Complete!", state="complete", expanded=False)
            st.rerun()

    # DISPLAY
    clean_status = str(st.session_state.status_flag).strip().upper().replace(".", "")
    if any(word in clean_status for word in ["OPEN", "ACTIVE"]):
        st.success(f"✅ STATUS: {clean_status}")
    elif "AWARDED" in clean_status:
        st.info(f"💰 STATUS: {clean_status}")
    else:
        st.error(f"🚨 STATUS: {clean_status}")

    st.divider()

    t1, t2, t3, t4, t5 = st.tabs(["📖 Overview", "🛠️ Tech Specs", "📝 Submission", "⚖️ Compliance", "💰 Award Details"])
    with t1: st.info(st.session_state.summary_ans)
    with t2: st.success(st.session_state.tech_ans)
    with t3: st.warning(st.session_state.submission_ans)
    with t4: st.error(st.session_state.compliance_ans)
    with t5: st.write(st.session_state.award_ans)
