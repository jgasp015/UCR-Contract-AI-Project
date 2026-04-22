import re
import st as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE INITIALIZATION
# ---------------------------
if "total_saved" not in st.session_state:
    st.session_state.total_saved = 480
if "active_bid_text" not in st.session_state:
    st.session_state.active_bid_text = None
if "active_bid_pages" not in st.session_state:
    st.session_state.active_bid_pages = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != "total_saved":
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. PDF & TEXT HELPERS
# ---------------------------
def extract_pdf_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    full_text_parts = []
    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        txt = txt.replace("\r", "\n")
        pages.append({"page_num": i, "text": txt})
        full_text_parts.append(f"\n\n<<<PAGE {i}>>>\n{txt}")
    return "\n".join(full_text_parts), pages

def remove_page_markers(text):
    if not text: return ""
    text = re.sub(r"<<<PAGE \d+>>>", "", text, flags=re.IGNORECASE)
    return text.strip()

# ---------------------------
# 3. AI ENGINE (TAXPAYER MODE)
# ---------------------------
def run_ai(text, prompt):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    # Deep context window to ensure we don't miss middle pages
    ctx = text[:25000] 
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "RULES: 1. NO INTROS. 2. VERTICAL BULLETS ONLY. 3. BE EXTREMELY BRIEF. 4. IF MISSING, SAY 'HIDEME'."
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return None if "HIDEME" in ans.upper() else ans
    except:
        return None

# ---------------------------
# 4. DATA EXTRACTION LOGIC
# ---------------------------
def get_scope_of_service(doc):
    # Specifically instructs AI to find the 'Remove' and 'Install' lines on Page 5
    prompt = "Look for the Scope of Service. List every task that starts with 'Remove' or 'Install' line by line."
    return run_ai(doc, prompt) or "No scope items found."

def get_rules_tab(doc):
    prompt = "List the 5% local business rule and the 10% penalty deduction rule line by line."
    return run_ai(doc, prompt) or "No specific rules found."

# ---------------------------
# 5. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# ---------------------------
# 6. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    
    # ONE-TIME DATA LOAD
    if not st.session_state.get("agency_name"):
        with st.status("🏗️ Scanning..."):
            st.session_state.agency_name = run_ai(doc, "Agency Name?")
            st.session_state.project_title = run_ai(doc, "Project Title?")
            st.session_state.status_flag = run_ai(doc, "Is this OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc, "Deadline Date?")
        st.rerun()

    # 3-LINE HEADER
    st.subheader("🏛️ Project Snapshot")
    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        header = f"● {status}"
        if st.session_state.due_date: header += f" | DUE: {st.session_state.due_date}"
        if "OPEN" in status: st.success(header)
        else: st.error(header)

    if st.session_state.agency_name: st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title: st.write(f"**📄 BID NAME:** {st.session_state.project_title}")
    st.divider()

    # TABS LOGIC
    if st.session_state.get("analysis_mode") == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1: st.info(run_ai(doc, "What specific data must be reported?"))
        with t2: st.error(run_ai(doc, "What counts as a violation?"))
        with t3: st.warning(run_ai(doc, "What are the dollar penalties?"))
        with t4: st.success(run_ai(doc, "How often are reports due?"))
        with t5: st.write(run_ai(doc, "Where are reports sent?"))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])
        with b1: st.info(get_scope_of_service(doc))
        with b2: st.success(run_ai(doc, "List specific hardware like laptops and antennas."))
        with b3: st.warning(run_ai(doc, "3 steps to apply via PlanetBids."))
        with b4: st.error(get_rules_tab(doc))
        with b5: st.write(run_ai(doc, "How is the winner picked (Points)?"))

else:
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])

    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            full_text, pages = extract_pdf_data(up)
            st.session_state.active_bid_text = full_text
            st.session_state.active_bid_pages = pages
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            full_text, pages = extract_pdf_data(up_c)
            st.session_state.active_bid_text = full_text
            st.session_state.active_bid_pages = pages
            st.session_state.analysis_mode = "Reporting"
            st.rerun()
