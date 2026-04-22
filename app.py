import re
import streamlit as st
import requests
from pypdf import PdfReader

# ---------------------------
# 1. STATE
# ---------------------------
DEFAULT_KEYS = {
    "total_saved": 480,
    "active_bid_text": None,
    "active_bid_pages": None,
    "analysis_mode": "Standard",
    "agency_name": None,
    "project_title": None,
    "status_flag": None,
    "due_date": None,
    "scope_result": None,
    "spec_result": None,
    "reporting_result": None,
    "violations_result": None,
    "remedies_result": None,
    "frequency_result": None,
    "admin_result": None,
    "scope_debug_result": None,
    "sla_debug_result": None,
}

for k, v in DEFAULT_KEYS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def clear_analysis_cache():
    keys_to_clear = [
        "agency_name", "project_title", "status_flag", "due_date",
        "scope_result", "spec_result",
        "reporting_result", "violations_result", "remedies_result",
        "frequency_result", "admin_result",
        "scope_debug_result", "sla_debug_result"
    ]
    for key in keys_to_clear:
        st.session_state[key] = None

def hard_reset():
    total_saved = st.session_state.get("total_saved", 480)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["total_saved"] = total_saved
    for k, v in DEFAULT_KEYS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# ---------------------------
# 2. LOW-LEVEL HELPERS
# ---------------------------
def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def normalize_line(line):
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    return line.strip()

def remove_page_markers(text):
    if not text:
        return ""
    text = re.sub(r"<<<PAGE \d+>>>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"PAGE \d+\s*---\.?", "", text, flags=re.IGNORECASE)
    return clean_text(text)

def bulletize(lines):
    if not lines:
        return None
    return "\n".join([f"* {line}" for line in lines])

def unique_keep_order(lines):
    seen = set()
    out = []
    for line in lines:
        key = re.sub(r"[^a-z0-9 ]+", "", line.lower()).strip()
        if key and key not in seen:
            seen.add(key)
            out.append(line)
    return out

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

# ---------------------------
# 3. PDF HELPERS
# ---------------------------
def extract_pdf_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    full_text_parts = []

    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        txt = clean_text(txt)

        page_obj = {
            "page_num": i,
            "text": txt
        }
        pages.append(page_obj)
        full_text_parts.append(f"\n\n<<<PAGE {i}>>>\n{txt}")

    return "\n".join(full_text_parts), pages

def get_page_range_text(pages, start_page, end_page):
    if not pages:
        return ""
    chunks = []
    for p in pages:
        if start_page <= p["page_num"] <= end_page:
            chunks.append(f"\n<<<PAGE {p['page_num']}>>>\n{p['text']}")
    return "\n".join(chunks)

def find_first_page_containing(pages, pattern):
    for p in pages or []:
        if re.search(pattern, p["text"], flags=re.IGNORECASE):
            return p["page_num"]
    return None

def is_toc_page(text):
    if not text:
        return False

    has_contents_word = bool(re.search(r"\b(table of contents|contents)\b", text, flags=re.IGNORECASE))
    dot_leader_hits = re.findall(r"\.{5,}\s*\d+\s*$", text, flags=re.MULTILINE)
    short_index_hits = re.findall(r"^\s*\d+(\.\d+)+\s+.*\.{3,}\s*\d+\s*$", text, flags=re.MULTILINE)

    return has_contents_word or len(dot_leader_hits) >= 4 or len(short_index_hits) >= 4

# ---------------------------
# 4. AI
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
                "content": (
                    "RULES: "
                    "1. NO INTROS. "
                    "2. USE ONLY VERTICAL BULLETS WITH *. "
                    "3. EVERY BULLET ON A NEW LINE. "
                    "4. DO NOT INVENT DETAILS. "
                    "5. DO NOT INCLUDE PAGE NUMBERS UNLESS ASKED. "
                    "6. IF MISSING, SAY HIDEME."
                )
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nTEXT:\n{text[:50000]}"
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
    except requests.Timeout:
        return "⚠️ Scanner timed out."
    except Exception as e:
        return f"⚠️ Scanner error: {e}"

# ---------------------------
# 5. SNAPSHOT EXTRACTION
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

    ai_ans = run_ai(doc_clean[:12000], "Agency name only.")
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

    ai_ans = run_ai(doc_clean[:16000], "Project title only.")
    return ai_ans or "Unknown"

def get_status(doc):
    doc_clean = remove_page_markers(doc)
    ai_ans = run_ai(doc_clean[:16000], "Is this project OPEN or CLOSED? Answer only OPEN or CLOSED.")
    return ai_ans or "UNKNOWN"

def get_due_date(doc):
    doc_clean = remove_page_markers(doc)
    return run_ai(doc_clean[:16000], "Deadline date only. If missing, say HIDEME.")

# ---------------------------
# 6. BID DOCUMENT EXTRACTION
# ---------------------------
def extract_scope_section_from_pages(pages):
    if not pages:
        return "", []

    scope_page = find_first_page_containing(pages, r"\bScope of Service\b|\bScope of Work\b")
    if not scope_page:
        return "", []

    start_page = scope_page
    end_page = min(scope_page + 4, len(pages))
    scope_window = get_page_range_text(pages, start_page, end_page)
    scope_window_clean = remove_page_markers(scope_window)

    m = re.search(
        r"(?:\b\d+\.\s*Scope of Service\b|\b\d+\.\s*Scope of Work\b|\bScope of Service\b|\bScope of Work\b)"
        r"(.*?)(?=\n\s*\d+\.\s+[A-Z]|\n\s*[A-Z][A-Z /&()\-]{6,}\n|\Z)",
        scope_window_clean,
        flags=re.IGNORECASE | re.DOTALL
    )

    if m:
        return clean_text(m.group(1)), list(range(start_page, end_page + 1))

    return clean_text(scope_window_clean), list(range(start_page, end_page + 1))

def get_scope_of_service(doc, pages):
    section, page_list = extract_scope_section_from_pages(pages)
    if not section:
        section = remove_page_markers(doc)

    lines = join_wrapped_lines(section.splitlines())

    results = []
    for line in lines:
        cleaned = re.sub(r"^[-•*]\s*", "", line).strip()
        cleaned = normalize_line(cleaned)

        if re.match(r"^(Remove|Install)\b", cleaned, flags=re.IGNORECASE):
            cleaned = cleaned.rstrip(" .") + "."
            if len(cleaned) > 10:
                results.append(cleaned)

    results = unique_keep_order(results)

    if results:
        return bulletize(results), page_list

    ai_ans = run_ai(
        section,
        "Find the Scope of Service or Scope of Work. List every task that starts with Remove or Install. Include the full task line."
    )
    return (ai_ans or "No Scope of Service lines found."), page_list

def get_specifications(doc, pages):
    section, _ = extract_scope_section_from_pages(pages)
    text = section if section else remove_page_markers(doc)

    ai_ans = run_ai(
        text,
        "List ONLY the specific technology, hardware, equipment, devices, docks, antennas, cameras, monitors, keyboards, laptops, cables, and mounting hardware mentioned."
    )
    return ai_ans or "No specifications found."

# ---------------------------
# 7. REPORTING / SLA EXTRACTION
# ---------------------------
def extract_sla_page_from_toc(pages):
    if not pages:
        return None

    toc_pages = [p for p in pages if is_toc_page(p["text"])]

    patterns = [
        r"SERVICE LEVEL AGREEMENTS\s*\(SLA\)\s*\.{3,}\s*(\d+)",
        r"Technical Service Level Agreements\s*\(SLA\)\s*\.{3,}\s*(\d+)",
        r"Bidder Response to Service Level Agreements\s*\.{3,}\s*(\d+)",
        r"Technical SLA General Requirements\s*\.{3,}\s*(\d+)",
        r"Trouble Ticket Stop Clock Conditions\s*\.{3,}\s*(\d+)"
    ]

    best_page = None

    for p in toc_pages:
        txt = p["text"]
        for pat in patterns:
            for m in re.finditer(pat, txt, flags=re.IGNORECASE):
                try:
                    page_num = int(m.group(1))
                    if 1 <= page_num <= len(pages):
                        if best_page is None or page_num < best_page:
                            best_page = page_num
                except Exception:
                    pass

    return best_page

def get_reporting_pages(pages):
    if not pages:
        return []

    hits = []

    sla_start = extract_sla_page_from_toc(pages)
    if sla_start:
        start = max(1, sla_start - 1)
        end = min(len(pages), sla_start + 20)
        for p in pages:
            if start <= p["page_num"] <= end and not is_toc_page(p["text"]):
                hits.append(p)
        if hits:
            return hits

    for p in pages:
        txt = p["text"]
        if not txt or is_toc_page(txt):
            continue

        has_real_sla_content = re.search(
            r"(Service Level Agreement|SLA\b|Stop Clock|Outage|Availability|Trouble Ticket|Ticket Stop Clock|Notification|Provisioning|Excessive Outage|Catastrophic Outage|Customer or Contractor)",
            txt,
            flags=re.IGNORECASE
        )

        has_content_language = re.search(
            r"(shall|must|response|objective|requirement|measurement|report|reports|reporting|minutes|hours|days|credit|penalty|threshold|restore|restoration|notify|ticket)",
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
        end_page = max(page_nums)
        text = get_page_range_text(pages, start_page, end_page)
        return remove_page_markers(text), list(range(start_page, end_page + 1))

    return remove_page_markers(doc), []

def get_reporting_data(doc, pages):
    text, page_list = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting pages, list ONLY what must be reported or measured, such as:
- outage reports
- response times
- restoration times
- service levels
- stop clock conditions
- ticket handling
- notification requirements
- monitoring thresholds

Do NOT include table of contents, page numbers, or section headers."""
    )
    return (ai_ans or "No reporting requirements found."), page_list

def get_violations(doc, pages):
    text, _ = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting pages, list all violations, breaches, or failure triggers such as:
- missed response times
- missed restoration times
- outage failures
- availability failures
- SLA failures
- contractor non-compliance events

Do NOT include page numbers or section headers."""
    )
    return ai_ans or "No violations found."

def get_remedies(doc, pages):
    text, _ = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting pages, list all remedies, penalties, service credits, corrective actions, or cure obligations.
Do NOT include page numbers or section headers."""
    )
    return ai_ans or "No remedies found."

def get_frequency(doc, pages):
    text, _ = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting pages, list all timing and frequency requirements such as:
- reporting frequency
- response windows
- restoration windows
- deadlines
- recurring intervals
- monitoring intervals

Do NOT include page numbers or section headers."""
    )
    return ai_ans or "No frequency requirements found."

def get_admin(doc, pages):
    text, _ = extract_reporting_text(doc, pages)

    ai_ans = run_ai(
        text,
        """From the actual SLA / reporting pages, list all administrative items such as:
- who reports
- who receives the notice
- submission duties
- ticket logging duties
- documentation requirements
- escalation requirements
- communication requirements

Do NOT include page numbers or section headers."""
    )
    return ai_ans or "No admin requirements found."

# ---------------------------
# 8. DEBUG
# ---------------------------
def get_scope_debug(pages):
    section, page_list = extract_scope_section_from_pages(pages)
    if not section:
        return "No scope section found."
    header = f"Detected Scope pages: {page_list}\n\n"
    return header + section[:4000]

def get_sla_debug(pages):
    hits = get_reporting_pages(pages)
    if not hits:
        return "No reporting / SLA pages detected."

    page_nums = [p["page_num"] for p in hits]
    sample = "\n\n".join([f"PAGE {p['page_num']}:\n{p['text'][:1200]}" for p in hits[:3]])
    return f"Detected SLA pages: {page_nums}\n\n{sample}"

# ---------------------------
# 9. CACHE BUILDERS
# ---------------------------
def build_bid_results():
    doc = st.session_state.active_bid_text
    pages = st.session_state.active_bid_pages

    if st.session_state.agency_name is None:
        st.session_state.agency_name = get_agency_name(doc)
    if st.session_state.project_title is None:
        st.session_state.project_title = get_project_title(doc)
    if st.session_state.status_flag is None:
        st.session_state.status_flag = get_status(doc)
    if st.session_state.due_date is None:
        st.session_state.due_date = get_due_date(doc)

    if st.session_state.scope_result is None:
        scope_text, scope_pages = get_scope_of_service(doc, pages)
        if scope_pages:
            scope_text = f"Detected Scope pages: {scope_pages}\n\n{scope_text}"
        st.session_state.scope_result = scope_text

    if st.session_state.spec_result is None:
        st.session_state.spec_result = get_specifications(doc, pages)

    if st.session_state.scope_debug_result is None:
        st.session_state.scope_debug_result = get_scope_debug(pages)

def build_reporting_results():
    doc = st.session_state.active_bid_text
    pages = st.session_state.active_bid_pages

    if st.session_state.reporting_result is None:
        reporting_text, reporting_pages = get_reporting_data(doc, pages)
        if reporting_pages:
            reporting_text = f"Detected SLA pages: {reporting_pages}\n\n{reporting_text}"
        st.session_state.reporting_result = reporting_text

    if st.session_state.violations_result is None:
        st.session_state.violations_result = get_violations(doc, pages)

    if st.session_state.remedies_result is None:
        st.session_state.remedies_result = get_remedies(doc, pages)

    if st.session_state.frequency_result is None:
        st.session_state.frequency_result = get_frequency(doc, pages)

    if st.session_state.admin_result is None:
        st.session_state.admin_result = get_admin(doc, pages)

    if st.session_state.sla_debug_result is None:
        st.session_state.sla_debug_result = get_sla_debug(pages)

# ---------------------------
# 10. SIDEBAR
# ---------------------------
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# ---------------------------
# 11. MAIN APP
# ---------------------------
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        if st.session_state.reporting_result is None:
            with st.status("Scanning reporting section..."):
                build_reporting_results()

        t1, t2, t3, t4, t5, t6 = st.tabs(
            ["📊 What to Report", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin", "🔎 Debug SLA"]
        )

        with t1:
            st.info(st.session_state.reporting_result)

        with t2:
            st.error(st.session_state.violations_result)

        with t3:
            st.warning(st.session_state.remedies_result)

        with t4:
            st.success(st.session_state.frequency_result)

        with t5:
            st.write(st.session_state.admin_result)

        with t6:
            st.code(st.session_state.sla_debug_result)

    else:
        if st.session_state.scope_result is None:
            with st.status("Scanning bid document..."):
                build_bid_results()

        st.subheader("🏛️ Project Snapshot")
        status = st.session_state.status_flag.upper() if st.session_state.status_flag else "UNKNOWN"
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

        b1, b2, b3 = st.tabs(["📖 Scope of Work", "🛠️ Specifications", "🔎 Debug Scope"])

        with b1:
            st.info(st.session_state.scope_result)

        with b2:
            st.success(st.session_state.spec_result)

        with b3:
            st.code(st.session_state.scope_debug_result)

else:
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])

    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            full_text, pages = extract_pdf_data(up)
            clear_analysis_cache()
            st.session_state.active_bid_text = full_text
            st.session_state.active_bid_pages = pages
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            full_text, pages = extract_pdf_data(up_c)
            clear_analysis_cache()
            st.session_state.active_bid_text = full_text
            st.session_state.active_bid_pages = pages
            st.session_state.analysis_mode = "Reporting"
            st.rerun()

    with tab3:
        st.text_input("Agency URL:", placeholder="Paste portal link here...", key="url_in")
