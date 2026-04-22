import re
import streamlit as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE
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
# 2. PDF HELPERS
# ---------------------------
def extract_pdf_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    full_text_parts = []

    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        txt = txt.replace("\r", "\n")
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()

        pages.append({
            "page_num": i,
            "text": txt
        })

        full_text_parts.append(f"\n\n<<<PAGE {i}>>>\n{txt}")

    return "\n".join(full_text_parts), pages

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def remove_page_markers(text):
    if not text:
        return ""
    text = re.sub(r"<<<PAGE \d+>>>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"PAGE \d+\s*---\.?", "", text, flags=re.IGNORECASE)
    return clean_text(text)

def normalize_line(line):
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line.strip()

def bulletize(lines):
    if not lines:
        return None
    return "\n".join([f"* {line}" for line in lines])

def unique_keep_order(lines):
    seen = set()
    out = []
    for line in lines:
        key = line.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(line)
    return out

def is_toc_page(text):
    if not text:
        return False

    # Lines like "27.3 SERVICE LEVEL AGREEMENTS .......... 88"
    dot_leader_hits = re.findall(r"\.{5,}\s*\d+\s*$", text, flags=re.MULTILINE)
    short_index_hits = re.findall(r"^\s*\d+(\.\d+)+\s+.*\.{3,}\s*\d+\s*$", text, flags=re.MULTILINE)
    has_contents_word = bool(re.search(r"\b(table of contents|contents)\b", text, flags=re.IGNORECASE))

    return has_contents_word or len(dot_leader_hits) >= 4 or len(short_index_hits) >= 4

def join_wrapped_lines(lines):
    rebuilt = []
    current = ""

    for raw in lines:
        line = normalize_line(raw)
        if not line:
            continue

        starts_new = (
            re.match(r"^[-•*]\s+", line) or
            re.match(r"^(Remove|Install)\b", line, flags=re.IGNORECASE) or
            re.match(r"^\d+(\.\d+)+\s+", line) or
            re.match(r"^[A-Z][A-Z /&()\-]{6,}$", line)
        )

        if starts_new:
            if current:
                rebuilt.append(current.strip())
            current = re.sub(r"^[-•*]\s*", "", line).strip()
        else:
            if current:
                current += " " + line
            else:
                current = line

    if current:
        rebuilt.append(current.strip())

    return rebuilt

def get_page_range_text(pages, start_page, end_page):
    if not pages:
        return ""
    chunks = []
    for p in pages:
        if start_page <= p["page_num"] <= end_page:
            chunks.append(p["text"])
    return "\n".join(chunks)

def find_first_page_containing(pages, pattern):
    for p in pages or []:
        if re.search(pattern, p["text"], flags=re.IGNORECASE):
            return p["page_num"]
    return None

# ---------------------------
# 3. AI ENGINE
# ---------------------------
def run_ai(text, prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system",
                "content": """RULES:
1. NO INTRO.
2. Use ONLY vertical bullet points with *.
3. Put EVERY bullet point on a NEW LINE.
4. Do not invent details.
5. Do not include page numbers unless explicitly asked.
6. If not found, say HIDEME."""
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nTEXT:\n{text[:45000]}"
            }
        ],
        "temperature": 0.0
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        r.raise_for_status()
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return None if "HIDEME" in ans.upper() else ans
    except Exception:
        return None

# ---------------------------
# 4. SNAPSHOT HELPERS
# ---------------------------
def get_agency_name(doc):
    doc_clean = remove_page_markers(doc)

    patterns = [
        r"\bCity of Sacramento\b",
        r"\bInternal Services Department\b",
        r"\bDepartment of General Services\b",
        r"\bCounty of [A-Za-z ]+\b",
        r"\bState of California\b"
    ]
    for pat in patterns:
        m = re.search(pat, doc_clean, flags=re.IGNORECASE)
        if m:
            return m.group(0)

    ai_ans = run_ai(doc_clean[:12000], "Agency name only. No extra words.")
    return ai_ans or "Unknown"

def get_project_title(doc):
    doc_clean = remove_page_markers(doc)

    patterns = [
        r"Project Title[:\s]+([^\n]+)",
        r"Solicitation Title[:\s]+([^\n]+)",
        r"Bid Title[:\s]+([^\n]+)",
        r"Request for Bids[:\s]+([^\n]+)",
        r"Request for Proposals[:\s]+([^\n]+)",
        r"Invitation for Bids[:\s]+([^\n]+)",
        r"IFB[:\s#-]+([^\n]+)",
        r"RFB[:\s#-]+([^\n]+)",
        r"RFP[:\s#-]+([^\n]+)"
    ]

    for pat in patterns:
        m = re.search(pat, doc_clean, flags=re.IGNORECASE)
        if m:
            val = normalize_line(m.group(1))
            if val and len(val) > 3:
                return val

    ai_ans = run_ai(doc_clean[:16000], "Project title only. No intro.")
    return ai_ans or "Unknown"

def get_status(doc):
    doc_clean = remove_page_markers(doc)
    ai_ans = run_ai(
        doc_clean[:16000],
        "Is this project OPEN or CLOSED? Answer only OPEN or CLOSED."
    )
    return ai_ans or "UNKNOWN"

def get_due_date(doc):
    doc_clean = remove_page_markers(doc)
    return run_ai(doc_clean[:16000], "Deadline date only. If none, say HIDEME.")

# ---------------------------
# 5. BID DOCUMENT / SCOPE
# ---------------------------
def extract_scope_section_from_pages(pages):
    if not pages:
        return ""

    start_page = find_first_page_containing(pages, r"\bScope of Service\b")
    if not start_page:
        return ""

    # Pull a few pages after scope starts because the section can span pages
    scope_window = get_page_range_text(pages, start_page, min(start_page + 4, len(pages)))
    scope_window = remove_page_markers(scope_window)

    m = re.search(
        r"(?:\b\d+\.\s*Scope of Service\b|\bScope of Service\b)(.*?)(?=\n\s*\d+\.\s+[A-Z]|\n\s*[A-Z][A-Z /&()\-]{6,}\n|\Z)",
        scope_window,
        flags=re.IGNORECASE | re.DOTALL
    )
    if m:
        return clean_text(m.group(1))

    return clean_text(scope_window)

def get_scope_of_service(doc, pages):
    section = extract_scope_section_from_pages(pages)
    if not section:
        section = remove_page_markers(doc)

    lines = join_wrapped_lines(section.splitlines())

    results = []
    for line in lines:
        cleaned = re.sub(r"^[-•*]\s*", "", line).strip()
        cleaned = normalize_line(cleaned)

        if re.match(r"^(Remove|Install)\b", cleaned, flags=re.IGNORECASE):
            cleaned = cleaned.rstrip(" .") + "."
            if len(cleaned) > len("Remove.") and len(cleaned) > len("Install."):
                results.append(cleaned)

    results = unique_keep_order(results)

    if results:
        return bulletize(results)

    ai_ans = run_ai(
        section,
        "List every full Scope of Service item that starts with Remove or Install. Include the complete line, not just the first word."
    )
    return ai_ans or "No Scope of Service lines found."

def get_tools_tab(doc, pages):
    section = extract_scope_section_from_pages(pages)
    text = section if section else remove_page_markers(doc)

    ai_ans = run_ai(
        text,
        "List the equipment, hardware, software, docks, antennas, cables, cameras, cabinets, monitors, keyboards, laptops, and mounting hardware line by line."
    )
    return ai_ans or "No tools or equipment found."

def get_apply_tab(doc):
    ai_ans = run_ai(
        remove_page_markers(doc),
        "List 3 simple application steps based only on the document."
    )
    return ai_ans or "No application steps found."

def get_rules_tab(doc):
    ai_ans = run_ai(
        remove_page_markers(doc),
        "List the main rules, local business requirements, compliance requirements, penalties, and mandatory conditions line by line."
    )
    return ai_ans or "No rules found."

def get_win_tab(doc):
    ai_ans = run_ai(
        remove_page_markers(doc),
        "Explain how the winner is selected in bullet points based only on the document."
    )
    return ai_ans or "No award criteria found."

# ---------------------------
# 6. REPORTING / SLA
# ---------------------------
def get_reporting_pages(pages):
    if not pages:
        return []

    hits = []

    for p in pages:
        txt = p["text"]
        if not txt:
            continue

        # Skip TOC/index pages
        if is_toc_page(txt):
            continue

        # Stronger indicators of actual SLA content, not index lines
        has_real_sla_content = re.search(
            r"(Service Level Agreement|SLA\b|Stop Clock|Outage|Availability|Trouble Ticket|Ticket Stop Clock|Notification|Provisioning|Excessive Outage|Catastrophic Outage|Customer or Contractor)",
            txt,
            flags=re.IGNORECASE
        )

        has_content_language = re.search(
            r"(shall|must|response|objective|requirement|measurement|report|reports|reporting|minutes|hours|days|credit|penalty|threshold)",
            txt,
            flags=re.IGNORECASE
        )

        if has_real_sla_content and has_content_language:
            hits.append(p)

    return hits

def extract_reporting_text(doc, pages):
    hits = get_reporting_pages(pages)

    if hits:
        page_nums = [p["page_num"] for p in hits]
        start_page = min(page_nums)
        end_page = min(max(page_nums) + 2, len(pages))
        text = get_page_range_text(pages, start_page, end_page)
        return remove_page_markers(text)

    # Fallback: search whole doc but without page markers
    return remove_page_markers(doc)

def get_reporting_data(doc, pages):
    text = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / Service Level Agreement section, list ONLY reporting and measurable compliance items such as:
- reporting obligations
- outage reporting
- response times
- restoration times
- service levels
- stop clock conditions
- ticket handling requirements
- metrics, thresholds, and notice requirements

Do NOT include table of contents, page numbers, section titles, or index lines."""
    )
    return ai_ans or "No reporting requirements found."

def get_violations(doc, pages):
    text = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA section, list all violation or failure triggers such as:
- missed response times
- missed restoration times
- service outages
- availability failures
- breach of SLA objective
- non-compliance events

Do NOT include page numbers or table of contents."""
    )
    return ai_ans or "No violations found."

def get_remedies(doc, pages):
    text = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA section, list all remedies, credits, corrective actions, cure actions, or contractor obligations after failure.
Do NOT include page numbers or table of contents."""
    )
    return ai_ans or "No remedies found."

def get_frequency(doc, pages):
    text = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA section, list all timing and frequency requirements such as:
- reporting frequency
- notice deadlines
- response windows
- restoration windows
- time measurements
- recurring intervals

Do NOT include page numbers or table of contents."""
    )
    return ai_ans or "No frequency requirements found."

def get_admin(doc, pages):
    text = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting section, list all admin items such as:
- submission method
- contact or party responsible
- notification duties
- documentation requirements
- reports to be provided
- ticket or recordkeeping expectations

Do NOT include page numbers or table of contents."""
    )
    return ai_ans or "No administrative requirements found."

# ---------------------------
# 7. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# ---------------------------
# 8. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text
    pages = st.session_state.active_bid_pages

    if not st.session_state.get("agency_name"):
        with st.status("Scanning..."):
            st.session_state.agency_name = get_agency_name(doc)
            st.session_state.project_title = get_project_title(doc)
            st.session_state.status_flag = get_status(doc)
            st.session_state.due_date = get_due_date(doc)
        st.rerun()

    st.subheader("🏛️ Project Snapshot")

    if st.session_state.status_flag:
        status = st.session_state.status_flag.upper()
        due = f" | DUE: {st.session_state.due_date}" if ("OPEN" in status and st.session_state.due_date) else ""
        if "OPEN" in status:
            st.success(f"● STATUS: {status}{due}")
        else:
            st.error(f"● STATUS: {status}")

    if st.session_state.agency_name:
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    if st.session_state.project_title:
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

    st.divider()

    if st.session_state.get("analysis_mode") == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])

        with t1:
            st.info(get_reporting_data(doc, pages))

        with t2:
            st.warning(get_violations(doc, pages))

        with t3:
            st.success(get_remedies(doc, pages))

        with t4:
            st.info(get_frequency(doc, pages))

        with t5:
            st.write(get_admin(doc, pages))

    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])

        with b1:
            st.info(get_scope_of_service(doc, pages))

        with b2:
            st.success(get_tools_tab(doc, pages))

        with b3:
            st.warning(get_apply_tab(doc))

        with b4:
            st.error(get_rules_tab(doc))

        with b5:
            st.write(get_win_tab(doc))

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

    with tab3:
        st.write("Paste or connect agency URL flow here later.")
