import re
import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state:
    st.session_state.total_saved = 480
if 'active_bid_text' not in st.session_state:
    st.session_state.active_bid_text = None
if 'active_bid_pages' not in st.session_state:
    st.session_state.active_bid_pages = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved':
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. PDF HELPERS ---
def extract_pdf_data(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []
    combined = []

    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text() or ""
        txt = txt.replace("\r", "\n")
        txt = re.sub(r"[ \t]+", " ", txt)
        txt = re.sub(r"\n{3,}", "\n\n", txt).strip()

        pages.append({
            "page_num": i,
            "text": txt
        })

        combined.append(f"\n\n<<<PAGE {i}>>>\n{txt}")

    return "\n".join(combined), pages

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

# --- 3. AI ENGINE ---
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
1. NO INTROS.
2. Use ONLY vertical bullet points (*).
3. Put EVERY bullet point on a NEW LINE.
4. Do not invent details.
5. If not found, say HIDEME."""
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nTEXT:\n{text[:35000]}"
            }
        ],
        "temperature": 0.0
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        r.raise_for_status()
        ans = r.json()["choices"][0]["message"]["content"].strip()
        return None if "HIDEME" in ans.upper() else ans
    except Exception:
        return None

# --- 4. GENERIC HELPERS ---
def join_wrapped_lines(lines):
    """
    Rebuild PDF-broken bullets where one bullet wraps into the next line.
    """
    rebuilt = []
    current = ""

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        line = re.sub(r"\s+", " ", line).strip()

        # start of a new bullet/item
        if re.match(r"^[-•*]\s+", line) or re.match(r"^(Remove|Install)\b", line, flags=re.IGNORECASE):
            if current:
                rebuilt.append(current.strip())
            current = re.sub(r"^[-•*]\s*", "", line).strip()
        else:
            # continuation of previous line
            if current:
                current += " " + line
            else:
                current = line

    if current:
        rebuilt.append(current.strip())

    return rebuilt

def bulletize(lines):
    if not lines:
        return None
    return "\n".join([f"* {x}" for x in lines])

def find_first_page_containing(pages, pattern):
    for p in pages or []:
        if re.search(pattern, p["text"], flags=re.IGNORECASE):
            return p
    return None

# --- 5. SNAPSHOT HELPERS ---
def get_agency_name(doc):
    # rule-based first
    m = re.search(r"City of Sacramento", doc, flags=re.IGNORECASE)
    if m:
        return "City of Sacramento"

    ai_ans = run_ai(doc[:12000], "Agency name only.")
    return ai_ans or "Unknown"

def get_project_title(doc):
    patterns = [
        r"Project Title[:\s]+([^\n]+)",
        r"RFP(?: No\.)?[:\s]+([^\n]+)",
        r"Invitation for Bids[:\s]+([^\n]+)",
        r"Request for Proposals[:\s]+([^\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, doc, flags=re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 3:
                return val

    ai_ans = run_ai(doc[:16000], "Project title only.")
    return ai_ans or "Unknown"

def get_status(doc):
    ai_ans = run_ai(doc[:16000], "Is this project OPEN or CLOSED? Answer only OPEN or CLOSED.")
    return ai_ans or "UNKNOWN"

def get_due_date(doc):
    ai_ans = run_ai(doc[:16000], "Deadline date only.")
    return ai_ans

# --- 6. SCOPE OF SERVICE ---
def get_scope_of_service(doc, pages):
    # Prefer page-level extraction so we do not lose the section
    page = find_first_page_containing(pages, r"\bScope of Service\b")
    scope_text = ""

    if page:
        scope_text = page["text"]

        # sometimes section continues to next page
        next_index = page["page_num"]
        if next_index < len(pages):
            scope_text += "\n" + pages[next_index]["text"]

    else:
        scope_text = doc

    scope_text = remove_page_markers(scope_text)

    # isolate the section
    m = re.search(
        r"(?:\b\d+\.\s*Scope of Service\b|\bScope of Service\b)(.*?)(?=\n\s*\d+\.\s+[A-Z]|\Z)",
        scope_text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if m:
        section = m.group(1).strip()
    else:
        section = scope_text

    raw_lines = section.splitlines()
    merged_lines = join_wrapped_lines(raw_lines)

    results = []
    for line in merged_lines:
        cleaned = re.sub(r"^[-•*]\s*", "", line).strip()

        if re.match(r"^(Remove|Install)\b", cleaned, flags=re.IGNORECASE):
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            cleaned = cleaned.rstrip(" .")
            results.append(cleaned + ".")

    if results:
        return bulletize(results)

    # fallback to AI only on narrowed section
    ai_ans = run_ai(
        section,
        "List every full Scope of Service item that starts with Remove or Install. Include the full text of each item."
    )
    return ai_ans or "No Scope of Service lines found."

# --- 7. REPORTING / COMPLIANCE ---
def get_reporting_pages(pages):
    hits = []
    for p in pages or []:
        txt = p["text"]
        if re.search(
            r"(Compliance Requirements|Reporting Requirements|Administrative Requirements|SLA|Service Level|Technical Requirements)",
            txt,
            flags=re.IGNORECASE
        ):
            hits.append(p)
    return hits

def extract_reporting_text(doc, pages):
    hits = get_reporting_pages(pages)

    if hits:
        text = "\n".join([p["text"] for p in hits[:3]])
        return remove_page_markers(text)

    return remove_page_markers(doc)

def get_reporting_data(doc, pages):
    text = extract_reporting_text(doc, pages)

    # remove page-only junk lines
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^PAGE \d+", s, flags=re.IGNORECASE):
            continue
        if re.match(r"^<<<PAGE \d+>>>$", s, flags=re.IGNORECASE):
            continue
        lines.append(s)

    cleaned_text = "\n".join(lines)

    ai_ans = run_ai(
        cleaned_text,
        "List specifically what data, responses, documentation, forms, attachments, compliance items, or reporting items must be submitted. Do not include page numbers."
    )
    return ai_ans or "No reporting requirements found."

def get_violations(doc, pages):
    text = extract_reporting_text(doc, pages)
    ai_ans = run_ai(
        text,
        "List all violations, defaults, non-compliance events, penalty triggers, or failure conditions line by line. Do not include page numbers."
    )
    return ai_ans or "No violations found."

def get_remedies(doc, pages):
    text = extract_reporting_text(doc, pages)
    ai_ans = run_ai(
        text,
        "List all remedies, cure periods, corrective actions, response requirements, or fixes line by line. Do not include page numbers."
    )
    return ai_ans or "No remedies found."

def get_frequency(doc, pages):
    text = extract_reporting_text(doc, pages)
    ai_ans = run_ai(
        text,
        "List all due dates, reporting intervals, deadlines, recurring schedules, or timing requirements line by line. Do not include page numbers."
    )
    return ai_ans or "No frequency requirements found."

def get_admin(doc, pages):
    text = extract_reporting_text(doc, pages)
    ai_ans = run_ai(
        text,
        "List all admin items such as contacts, submission methods, portals, forms, approvals, certifications, and administrative steps line by line. Do not include page numbers."
    )
    return ai_ans or "No administrative requirements found."

# --- 8. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 9. MAIN APP ---
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
            tools_ans = run_ai(
                remove_page_markers(doc),
                "List the hardware, antennas, cables, laptops, docks, cabinets, cameras, mounting hardware, and equipment line by line."
            )
            st.success(tools_ans or "No tools or equipment found.")

        with b3:
            apply_ans = run_ai(
                remove_page_markers(doc),
                "List 3 simple steps to apply."
            )
            st.warning(apply_ans or "No application steps found.")

        with b4:
            rules_ans = run_ai(
                remove_page_markers(doc),
                "List the main rules, local business requirements, penalties, and compliance requirements line by line."
            )
            st.error(rules_ans or "No rules found.")

        with b5:
            win_ans = run_ai(
                remove_page_markers(doc),
                "Explain how the winner is selected in bullet points."
            )
            st.write(win_ans or "No award criteria found.")

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
