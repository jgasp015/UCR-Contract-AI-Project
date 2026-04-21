import streamlit as st
import requests
from pypdf import PdfReader
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io
import re

# --- 1. SESSION STATE (STRICTLY ISOLATED) ---
def init_state():
    keys = {
        'active_bid_text': None, 'analysis_mode': "Standard",
        'agency_name': None, 'project_title': None, 'status_flag': None,
        'detected_due_date': None, 'summary_ans': None, 'tech_ans': None, 
        'submission_ans': None, 'compliance_ans': None, 'award_ans': None, 
        'bid_details': None, 'report_ans': None, 'total_saved': 0,
        'portal_hits': [], 
        'portal_session': requests.Session()
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
    system_content = "You are a Public Records Assistant. RULES: 1. MOM-TEST. 2. NO REPEATING. 3. NO FILLER."
    payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": system_content}, {"role": "user", "content": f"{specific_prompt}\n\nTEXT:\n{context_text}"}], "temperature": 0.0}
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res = response.json()['choices'][0]['message']['content'].strip()
        if is_header: return res.split('\n')[0].strip()
        return format_vertical_list(res)
    except: return "N/A"

# --- 3. ENGINE B: PERFECT REPORTING LOGIC (UNTOUCHED) ---
def reporting_query(full_text, specific_prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    start_point = int(len(full_text) * 0.5)
    context_text = full_text[start_point:] 
    system_content = "You are a Compliance Assistant. Explain HOW to report and SLA rules."
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
        if not l or any(x in l for x in ["hello", "neighbor", "here is"]): continue
        if l in seen: continue 
        display_line = line.strip()
        if not display_line.startswith("-"): display_line = f"- {display_line}"
        clean_lines.append(display_line)
        seen.add(l)
    return "\n\n".join(clean_lines[:15])

# --- 4. ENGINE C: PORTAL DEEP-SCANNER (BYPASSING SESSION ERRORS) ---
def deep_portal_scanner(url):
    """Initial scan that establishes a persistent session and mimics a browser."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
        }
        # First visit to the base domain to get the 'Asp.Net' session cookie
        st.session_state.portal_session.get("https://camisvr.co.la.ca.us/LACoBids/", headers=headers, timeout=10)
        r = st.session_state.portal_session.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        keywords = ["SOFTWARE", "IT ", "TECHNOLOGY", "NETWORK", "SAAS", "DATA", "CPU", "GPU", "SECURITY"]
        results = []
        for row in soup.find_all('tr'):
            row_text = row.get_text().upper()
            if any(k in row_text for k in keywords):
                cols = row.find_all('td')
                link_tag = row.find('a', href=True)
                if link_tag and len(cols) >= 2:
                    solicitation = link_tag.get_text(strip=True)
                    raw_href = link_tag['href']
                    
                    # Construct Detail URL
                    bid_id_match = re.search(r"\'(\d+)\'", raw_href)
                    bid_id = bid_id_match.group(1) if bid_id_match else ""
                    final_url = f"https://camisvr.co.la.ca.us/LACoBids/BidLookUp/BidDetail?bidNumber={bid_id}"

                    raw_desc = cols[1].get_text(strip=True).replace(solicitation, "")
                    description = raw_desc.split("Commodity:")[0].strip()
                    commodity = raw_desc.split("Commodity:")[1].strip() if "Commodity:" in raw_desc else "IT Service"
                    
                    results.append({"name": solicitation, "description": description, "commodity": commodity, "url": final_url})
        return list({res['name']: res for res in results}.values())[:10]
    except: return []

def analyze_portal_document(bid_url):
    """Bypasses the 'Object Reference' error by setting proper Referer headers."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://camisvr.co.la.ca.us/LACoBids/BidLookUp/OpenBidList'
        }
        # Get the detail page
        r_page = st.session_state.portal_session.get(bid_url, headers=headers, timeout=15)
        soup = BeautifulSoup(r_page.text, 'html.parser')
        
        # Look for PDF links on the detail page
        pdf_link = None
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            if any(x in href for x in [".pdf", "getattachment", "download"]):
                pdf_link = urljoin("https://camisvr.co.la.ca.us", a['href'])
                break
        
        if not pdf_link:
            return "No readable PDF found. The portal may require you to solve a CAPTCHA or Login manually."

        # Download PDF using the same session
        r_pdf = st.session_state.portal_session.get(pdf_link, headers=headers, timeout=30)
        pdf_file = io.BytesIO(r_pdf.content)
        reader = PdfReader(pdf_file)
        full_text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        
        if len(full_text) < 100: return "PDF text is restricted or image-based. Please upload manually in 'Bid Document' tab."

        summary = bid_query(full_text, "What are the project goals?")
        tech = bid_query(full_text, "What software/hardware is needed?")
        legal = bid_query(full_text, "What are the insurance and legal rules?")
        
        return f"### 📖 Project Goals\n{summary}\n\n### 🛠️ Tech Required\n{tech}\n\n### ⚖️ Legal & Insurance\n{legal}"
    except Exception as e:
        return f"Access Blocked: {str(e)}. The government portal is protecting the file from automated scans."

# --- 5. UI LAYOUT ---
st.title("🏛️ Public Sector Contract Analyzer")

if st.session_state.active_bid_text:
    if st.button("⬅️ Back"):
        st.session_state.active_bid_text = None
        clear_document_data(); st.rerun()
    doc = st.session_state.active_bid_text
    if st.session_state.analysis_mode == "Reporting":
        if not st.session_state.report_ans:
            st.session_state.report_ans = reporting_query(doc, "Explain HOW to report and SLA rules.")
            st.rerun()
        st.info("### 📊 Contractor Guide: Service Performance"); st.markdown(st.session_state.report_ans)
    else:
        if not st.session_state.agency_name:
            st.session_state.agency_name = bid_query(doc, "Agency?", is_header=True)
            st.session_state.project_title = bid_query(doc, "Project?", is_header=True)
            st.session_state.detected_due_date = bid_query(doc, "Deadline?", is_header=True)
            st.rerun()
        st.success(f"● OPEN | Deadline: {st.session_state.detected_due_date}"); st.subheader(st.session_state.project_title); st.write(f"**{st.session_state.agency_name}**")
        if not st.session_state.summary_ans:
            st.session_state.bid_details = bid_query(doc, "ID and Email."); st.session_state.summary_ans = bid_query(doc, "Goals?")
            st.session_state.tech_ans = bid_query(doc, "Tech?"); st.session_state.submission_ans = bid_query(doc, "Steps?")
            st.session_state.compliance_ans = bid_query(doc, "Legal?"); st.session_state.award_ans = bid_query(doc, "Award?")
            st.rerun()
        t_det, t_plan, t_tech, t_apply, t_legal, t_award = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])
        t_det.markdown(st.session_state.bid_details); t_plan.info(st.session_state.summary_ans)
        t_tech.success(st.session_state.tech_ans); t_apply.warning(st.session_state.submission_ans)
        t_legal.error(st.session_state.compliance_ans); t_award.write(st.session_state.award_ans)

else:
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])
    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up).pages])
            st.session_state.analysis_mode = "Standard"; clear_document_data(); st.rerun()
    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = "".join([p.extract_text() for p in PdfReader(up_c).pages])
            st.session_state.analysis_mode = "Reporting"; clear_document_data(); st.rerun()
    with t3:
        url_in = st.text_input("Agency Portal URL:", value="", placeholder="Paste government bid URL...")
        if st.button("Search for IT Bids"):
            if url_in:
                with st.spinner("Establishing secure session and scanning portal..."):
                    st.session_state.portal_hits = deep_portal_scanner(url_in)
            else: st.error("Enter a URL first.")
        
        if st.session_state.portal_hits:
            st.success(f"Found {len(st.session_state.portal_hits)} IT Opportunities:")
            for bid in st.session_state.portal_hits:
                with st.expander(f"🖥️ {bid['description']} ({bid['name']})"):
                    st.caption(f"📦 Commodity: {bid['commodity']}")
                    # Using link_button for stable redirection
                    st.link_button("Open Listing in New Tab", bid['url'])
                    st.divider()
                    if st.button(f"Deep Analyze {bid['name']}", key=f"btn_{bid['name']}"):
                        with st.spinner("Scraping attached document..."):
                            analysis = analyze_portal_document(bid['url'])
                            st.markdown(analysis)
