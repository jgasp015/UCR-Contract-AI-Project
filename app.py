import streamlit as st
import requests
import time
import os
from pypdf import PdfReader
from datetime import datetime
from bs4 import BeautifulSoup

# --- 1. SESSION STATE (STRICTLY ISOLATED) ---
def init_state():
    keys = {
        'all_bids': [], 'active_bid_text': None, 
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'analysis_mode': "Standard",
        'summary_ans': None, 'tech_ans': None, 'submission_ans': None,
        'compliance_ans': None, 'award_ans': None, 'bid_details': None,
        'report_ans': None, 'total_saved': 0
    }
    for k, v in keys.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

def clear_document_data():
    for key in ['agency_name', 'project_title', 'status_flag', 'detected_due_date', 
                'summary_ans', 'tech_ans', 'submission_ans', 'compliance_ans', 
                'award_ans', 'bid_details', 'report_ans']:
        st.session_state[key] = None

try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    st.error("🔑 GROQ_API_KEY missing!")
    st.stop()

API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- 2. ENGINE A: PERFECT BID LOGIC (UNTOUCHED) ---

def bid_query(full_text, specific_prompt, is_header=False):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    if is_header: context_text = full_text[:8000]
    elif any(x in specific_prompt.lower() for x in ["tech", "goal", "award", "software"]):
        context_text = full_text[-15000:] 
    elif any(x in specific_prompt.lower() for x in ["rule", "legal", "insurance"]):
        context_text = full_text[2000:20000] 
    else: context_text = full_text[:8000] + "\n[...]\n" + full_text[-10000:]

    system_content = """You are a Public Records Assistant. RULES: 1. MOM-TEST. 2. NO REPEATING. 3. NO FILLER. 4. START IMMEDIATELY with '-'."""
    if is_header: system_content = "Return ONLY the name requested. No labels."

    payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{context_text}"}], "temperature": 0.0}
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        if is_header:
            for skip in ["Agency:", "Project:", "Status:", "Deadline:", "- "]: res = res.replace(skip, "")
            return res.split('\n')[0].strip()
        return format_vertical_list(res)
    except: return "N/A"

# --- 3. ENGINE B: PERFECT REPORTING LOGIC (UNTOUCHED) ---

def reporting_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    start_point = int(len(full_text) * 0.5)
    context_text = full_text[start_point:] 
    system_content = """You are a Compliance Assistant for new contractors. Explain exactly HOW to report and WHAT to achieve. 
    RULES: 1. HOW TO REPORT (TTRT/Phone). 2. SERVICE PROMISES (Premier %). 3. STOP CLOCK reasons. 4. MONTHLY REPORTS."""
    payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{context_text}"}], "temperature": 0.0}
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return format_vertical_list(response.json()['choices'][0]['message']['content'].strip())
    except: return "N/A"

def format_vertical_list(text):
    lines = text.split('\n')
    clean_lines = []
    seen = set()
    for line in lines:
        l = line.strip().lower()
        if not l or any(x in l for x in ["hello", "neighbor", "here is", "following"]): continue
        if l in seen: continue 
        display_line = line.strip()
        if not display_line.startswith("-"): display_line = f"- {display_line}"
        clean_lines.append(display_line)
        seen.add(l)
    return "\n\n".join(clean_lines[:15])

# --- 4. ENGINE C: ISOLATED PORTAL SCANNER (THE FIX) ---

def scrape_it_bids(url):
    """Scrapes LA County Portal specifically for IT-related bids."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        it_keywords = ["SOFTWARE", "IT", "TECHNOLOGY", "NETWORK", "SAAS", "HARDWARE", "COMPUTER", "DATA"]
        found_bids = []
        
        for link in soup.find_all('a'):
            text = link.get_text().strip().upper()
            href = link.get('href', '')
            if any(key in text for key in it_keywords):
                found_bids.append({"name": text, "url": href})
        return found_bids[:10]
    except: return None

def analyze_portal_item(bid_name):
    """AI provides a quick-scan summary based on the IT Bid Name."""
    prompt = f"This is an IT bid title: {bid_name}. Based on typical LA County IT standards, list: 1. Main Goal, 2. Required Tech, 3. Legal/Insurance needs, 4. Award criteria."
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "system", "content": "You are an IT Bid Analyst. Use short vertical points."},
                     {"role": "user", "content": prompt}],
        "temperature": 0.0
    }
    try:
        r = requests.post(API_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json=payload)
        return r.json()['choices'][0]['message']['content']
    except: return "Analysis pending document upload."

# --- 5. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_document_data()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            with st.status("📊 Scanning Compliance..."):
                prompt = "Explain HOW to report, SLA targets, Stop Clocks, and Monthly Reports."
                st.session_state.report_ans = reporting_query(doc, prompt)
                st.rerun()
        st.info("### 📊 Contractor Guide: Service Performance")
        st.markdown(st.session_state.report_ans)

    else:
        if not st.session_state.agency_name:
            with st.status("Analyzing..."):
                st.session_state.agency_name = bid_query(doc, "Agency?", is_header=True)
                st.session_state.project_title = bid_query(doc, "Project name?", is_header=True)
                raw_date = bid_query(doc, "Deadline?", is_header=True)
                st.session_state.detected_due_date = raw_date
                st.rerun()

        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}")
        st.subheader(st.session_state.project_title)
        st.write(f"**{st.session_state.agency_name}**")
        st.divider()

        if not st.session_state.summary_ans:
            with st.status("Gathering Specific Facts..."):
                st.session_state.bid_details = bid_query(doc, "ID and Email only.")
                st.session_state.summary_ans = bid_query(doc, "Project goals?")
                st.session_state.tech_ans = bid_query(doc, "Software/Hardware needed?")
                st.session_state.submission_ans = bid_query(doc, "Apply steps.")
                st.session_state.compliance_ans = bid_query(doc, "Insurance/Conduct.")
                st.session_state.award_ans = bid_query(doc, "Winning criteria?")
                st.rerun()

        t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t_det.markdown(st.session_state.bid_details)
        t_plan.info(st.session_state.summary_ans)
        t_tech.success(st.session_state.tech_ans)
        t_apply.warning(st.session_state.submission_ans)
        t_legal.error(st.session_state.compliance_ans)
        t_award.write(st.session_state.award_ans)

else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"
            clear_document_data()
            st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"
            clear_document_data()
            st.rerun()
    with t3:
        url_in = st.text_input("Agency URL:", value="https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList")
        if st.button("Filter IT Bids"):
            with st.spinner("Scraping Technology Opportunities..."):
                it_results = scrape_it_bids(url_in)
                if it_results:
                    for item in it_results:
                        with st.expander(f"🖥️ {item['name']}"):
                            st.write(f"[Link to Official Bid]({item['url']})")
                            st.write("---")
                            st.markdown(analyze_portal_item(item['name']))
                else:
                    st.warning("No IT-specific bids found on the first page.")
