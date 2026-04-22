import re
import streamlit as st
import requests
from pypdf import PdfReader

# --- 1. STATE ---
if 'total_saved' not in st.session_state:
    st.session_state.total_saved = 480
if 'active_bid_text' not in st.session_state:
    st.session_state.active_bid_text = None

def hard_reset():
    for key in list(st.session_state.keys()):
        if key != 'total_saved':
            del st.session_state[key]
    st.rerun()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

# --- 2. PDF HELPERS ---
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        txt = page.extract_text()
        if not txt:
            txt = ""
        pages.append(f"\n\n--- PAGE {i} ---\n{txt}")

    return "\n".join(pages)

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

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
4. If the answer is missing, say HIDEME.
5. Do not invent details that are not in the text."""
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

# --- 4. SECTION FINDERS ---
def find_section(text, start_patterns, end_patterns=None):
    text = clean_text(text)
    if not text:
        return None

    for start_pat in start_patterns:
        start_match = re.search(start_pat, text, flags=re.IGNORECASE | re.DOTALL)
        if start_match:
            start_index = start_match.start()

            if end_patterns:
                end_index = len(text)
                search_area = text[start_match.end():]

                for end_pat in end_patterns:
                    end_match = re.search(end_pat, search_area, flags=re.IGNORECASE | re.DOTALL)
                    if end_match:
                        candidate_end = start_match.end() + end_match.start()
                        if candidate_end < end_index:
                            end_index = candidate_end

                return text[start_index:end_index].strip()

            return text[start_index:].strip()

    return None

def extract_bullets_from_section(section_text):
    if not section_text:
        return None

    lines = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if re.match(r"^[\-\u2022\*\•]+\s*", line):
            line = re.sub(r"^[\-\u2022\*\•]+\s*", "", line).strip()
            if line:
                if not line.endswith("."):
                    line += "."
                lines.append(f"* {line}")

    return "\n".join(lines) if lines else None

# --- 5. STANDARD BID EXTRACTION ---
def extract_scope_chunk(doc):
    return find_section(
        doc,
        start_patterns=[
            r"\b\d+\.\s*Scope of Service\b",
            r"\bScope of Service\b"
        ],
        end_patterns=[
            r"\n\s*\d+\.\s+[A-Z]",
            r"\n\s*[A-Z][A-Za-z /&]{3,}:\s",
            r"\n\s*Proposal Requirements\b",
            r"\n\s*LBE Participation Requirements\b"
        ]
    )

def extract_scope_lines(scope_text):
    if not scope_text:
        return None

    lines = []
    for raw_line in scope_text.splitlines():
        line = raw_line.strip()
        line = re.sub(r"^[\-\u2022\*\•]+\s*", "", line).strip()

        if re.match(r"^(Remove|Install)\b", line, flags=re.IGNORECASE):
            if not line.endswith("."):
                line += "."
            lines.append(f"* {line}")

    return "\n".join(lines) if lines else None

def get_scope_of_service(doc):
    scope_chunk = extract_scope_chunk(doc)

    parsed = extract_scope_lines(scope_chunk)
    if parsed:
        return parsed

    if scope_chunk:
        ai_ans = run_ai(scope_chunk, "List every item that starts with Remove or Install.")
        if ai_ans:
            return ai_ans

    return "No Scope of Service lines found."

# --- 6. REPORTING / COMPLIANCE EXTRACTION ---
def extract_reporting_chunk(doc):
    return find_section(
        doc,
        start_patterns=[
            r"\bCompliance Requirements\b",
            r"\bReporting Requirements\b",
            r"\bAdministrative Requirements\b",
            r"\bPerformance Requirements\b",
            r"\bService Level Agreement\b",
            r"\bSLA\b",
            r"\bTechnical Requirements\b"
        ],
        end_patterns=[
            r"\n\s*\d+\.\s+[A-Z]",
            r"\n\s*[A-Z][A-Za-z /&]{3,}:\s"
        ]
    )

def get_reporting_data(doc):
    section = extract_reporting_chunk(doc)

    if section:
        bullets = extract_bullets_from_section(section)
        if bullets:
            return bullets

        ai_ans = run_ai(
            section,
            "List specifically what data must be reported or submitted line by line."
        )
        if ai_ans:
            return ai_ans

    ai_fallback = run_ai(
        doc,
        "Find only the compliance or reporting requirements. List exactly what data, fields, responses, or documentation must be submitted line by line."
    )
    return ai_fallback or "No reporting requirements found."

def get_violations(doc):
    section = extract_reporting_chunk(doc)

    if section:
        ai_ans = run_ai(
            section,
            "List penalties, violations, non-compliance triggers, defaults, or failures mentioned in this text line by line."
        )
        if ai_ans:
            return ai_ans

    ai_fallback = run_ai(
        doc,
        "Find all violations, penalties, defaults, non-compliance events, or failure conditions. List them line by line."
    )
    return ai_fallback or "No violations found."

def get_remedies(doc):
    section = extract_reporting_chunk(doc)

    if section:
        ai_ans = run_ai(
            section,
            "List all remedies, cure periods, corrective actions, recovery steps, or required fixes line by line."
        )
        if ai_ans:
            return ai_ans

    ai_fallback = run_ai(
        doc,
        "Find all remedies, cure periods, corrective actions, or required response actions. List them line by line."
    )
    return ai_fallback or "No remedies found."

def get_frequency(doc):
    section = extract_reporting_chunk(doc)

    if section:
        ai_ans = run_ai(
            section,
            "List all time intervals, due dates, reporting frequency, deadlines, or recurring schedules line by line."
        )
        if ai_ans:
            return ai_ans

    ai_fallback = run_ai(
        doc,
        "Find all frequencies, due dates, reporting schedules, deadlines, and recurring timing requirements. List them line by line."
    )
    return ai_fallback or "No frequency requirements found."

def get_admin(doc):
    section = extract_reporting_chunk(doc)

    if section:
        ai_ans = run_ai(
            section,
            "List all admin contacts, portals, forms, submission methods, approval steps, and administrative requirements line by line."
        )
        if ai_ans:
            return ai_ans

    ai_fallback = run_ai(
        doc,
        "Find all administrative requirements including portals, submission methods, contacts, approvals, forms, and required documentation. List them line by line."
    )
    return ai_fallback or "No administrative requirements found."

# --- 7. SNAPSHOT HELPERS ---
def get_agency_name(doc):
    ai_ans = run_ai(doc[:12000], "Agency name only.")
    return ai_ans or "Unknown"

def get_project_title(doc):
    ai_ans = run_ai(doc[:16000], "Project title only.")
    return ai_ans or "Unknown"

def get_status(doc):
    ai_ans = run_ai(doc[:16000], "Is this project OPEN or CLOSED? Answer only OPEN or CLOSED.")
    return ai_ans or "UNKNOWN"

def get_due_date(doc):
    ai_ans = run_ai(doc[:16000], "Deadline date only.")
    return ai_ans

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
            st.info(get_reporting_data(doc))

        with t2:
            st.warning(get_violations(doc))

        with t3:
            st.success(get_remedies(doc))

        with t4:
            st.info(get_frequency(doc))

        with t5:
            st.write(get_admin(doc))

    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])

        with b1:
            st.info(get_scope_of_service(doc))

        with b2:
            tools_ans = run_ai(doc, "List the hardware, software, tools, cables, antennas, laptops, docks, cameras, and equipment line by line.")
            st.success(tools_ans or "No tools or equipment found.")

        with b3:
            apply_ans = run_ai(doc, "List 3 simple steps to apply.")
            st.warning(apply_ans or "No application steps found.")

        with b4:
            rules_ans = run_ai(doc, "List the main rules, local business requirements, penalties, and compliance requirements line by line.")
            st.error(rules_ans or "No rules found.")

        with b5:
            win_ans = run_ai(doc, "Explain how the winner is selected in bullet points.")
            st.write(win_ans or "No award criteria found.")

else:
    st.title("🏛️ Reporting Tool")
    tab1, tab2, tab3 = st.tabs(["📄 Bid Document", "📊 Compliance Requirements", "🔗 Agency URL"])

    with tab1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="u1")
        if up:
            st.session_state.active_bid_text = extract_pdf_text(up)
            st.session_state.analysis_mode = "Standard"
            st.rerun()

    with tab2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="u2")
        if up_c:
            st.session_state.active_bid_text = extract_pdf_text(up_c)
            st.session_state.analysis_mode = "Reporting"
            st.rerun()

    with tab3:
        st.write("Paste or connect agency URL flow here later.")
