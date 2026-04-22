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

# --- 2. HELPERS ---
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    pages = []

    for i, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if not page_text:
            page_text = ""
        pages.append(f"\n\n--- PAGE {i} ---\n{page_text}")

    return "\n".join(pages)

def clean_text(text):
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def extract_scope_chunk(full_text):
    if not full_text:
        return None

    text = clean_text(full_text)

    patterns = [
        r"(?is)\b4\.\s*Scope of Service\b(.*?)(?=\n\s*\d+\.\s+[A-Z])",
        r"(?is)\bScope of Service\b(.*?)(?=\n\s*\d+\.\s+[A-Z])",
        r"(?is)\b4\.\s*Scope of Service\b(.*)",
        r"(?is)\bScope of Service\b(.*)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            chunk = match.group(0).strip()
            if len(chunk) > 50:
                return chunk

    return None

def extract_remove_install_lines(scope_text):
    if not scope_text:
        return None

    lines = []
    for raw_line in scope_text.splitlines():
        line = raw_line.strip()

        # Remove bullets/dashes first
        line = re.sub(r"^[\-\u2022\*\•]+\s*", "", line).strip()

        if re.match(r"^(Remove|Install)\b", line, flags=re.IGNORECASE):
            if not line.endswith("."):
                line += "."
            lines.append(f"* {line}")

    return "\n".join(lines) if lines else None

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
4. If the user asks for Scope of Service, list only the direct scope items.
5. If missing, say HIDEME."""
            },
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{text}"}
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
        ans = r.json()['choices'][0]['message']['content'].strip()
        return None if "HIDEME" in ans.upper() else ans
    except Exception:
        return None

def get_scope_of_service(doc):
    scope_chunk = extract_scope_chunk(doc)

    # First try direct parsing from the extracted section
    parsed_lines = extract_remove_install_lines(scope_chunk)
    if parsed_lines:
        return parsed_lines

    # Fallback: send only the scope chunk to the AI
    if scope_chunk:
        ai_answer = run_ai(
            scope_chunk,
            "List every single scope item that starts with Remove or Install, line by line."
        )
        if ai_answer:
            return ai_answer

    return "No Scope of Service lines found."

# --- 3. UI SIDEBAR ---
with st.sidebar:
    st.header("Project Performance")
    st.metric("Total Est. Time Saved", f"{st.session_state.total_saved} mins")
    if st.button("🏠 Home / Reset App"):
        hard_reset()
    st.caption("UCR Master of Science - Jeffrey Gaspar")

# --- 4. MAIN NAVIGATION ---
if st.session_state.active_bid_text:
    doc = st.session_state.active_bid_text

    # --- BID DOCUMENT HEADER (3 LINES ONLY) ---
    if not st.session_state.get('agency_name'):
        with st.status("Scanning..."):
            st.session_state.agency_name = run_ai(doc[:12000], "Agency Name?")
            st.session_state.project_title = run_ai(doc[:12000], "Project Title?")
            st.session_state.status_flag = run_ai(doc[:12000], "Is this project OPEN or CLOSED?")
            st.session_state.due_date = run_ai(doc[:12000], "Deadline Date?")
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

    # --- TABS ---
    if st.session_state.get('analysis_mode') == "Reporting":
        t1, t2, t3, t4, t5 = st.tabs(["📊 Reporting", "⚠️ Violations", "💊 Remedies", "📅 Frequency", "🏢 Admin"])
        with t1:
            st.info(run_ai(doc, "List specifically what data must be reported line by line."))
    else:
        b1, b2, b3, b4, b5 = st.tabs(["📖 Scope of Service", "🛠️ Tools", "📝 Apply", "⚖️ Rules", "💰 Win"])

        with b1:
            st.info(get_scope_of_service(doc))

        with b2:
            st.success(run_ai(doc, "List the hardware like laptops, antennas, cables line by line."))

        with b3:
            st.warning(run_ai(doc, "3 simple steps to apply via PlanetBids."))

        with b4:
            st.error(run_ai(doc, "Explain the 5% local business rule and the 10% penalty."))

        with b5:
            st.write(run_ai(doc, "How do they pick the winner?"))

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
