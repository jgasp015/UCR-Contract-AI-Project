import streamlit as st
import requests
from pypdf import PdfReader
import io
import time

# --- SILO 1: SESSION & STATE ---
def init_state():
    keys = {
        'active_bid_text': None,
        'analysis_mode': "Standard",
        'portal_hits': [],
        'portal_session': requests.Session(),
        'agency_name': None,
        'project_title': None,
        'detected_due_date': None,
        'summary_ans': None,
        'tech_ans': None,
        'submission_ans': None,
        'compliance_ans': None,
        'award_ans': None,
        'bid_details': None,
        'report_ans': None,
        'last_error': None
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def reset_analysis():
    for k in [
        'agency_name', 'project_title', 'detected_due_date',
        'summary_ans', 'tech_ans', 'submission_ans',
        'compliance_ans', 'award_ans', 'bid_details',
        'report_ans', 'last_error'
    ]:
        st.session_state[k] = None

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: SMART RETRY AI ENGINE ---
def run_ai(text, prompt, system_msg, context_slice="full"):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    if not text or not text.strip():
        return "⚠️ No readable text found in the PDF."

    if context_slice == "start":
        ctx = text[:15000]
    else:
        if len(text) <= 20000:
            ctx = text
        else:
            ctx = text[:10000] + "\n[...]\n" + text[-10000:]

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"{prompt}\n\nTEXT:\n{ctx}"}
        ],
        "temperature": 0.0
    }

    for attempt in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

            # Save debug info
            st.session_state.last_error = f"HTTP {response.status_code}"

            # Handle non-200 errors first
            if response.status_code != 200:
                raw_text = response.text[:500]
                st.session_state.last_error = f"HTTP {response.status_code}: {raw_text}"

                if response.status_code == 429:
                    time.sleep(2)
                    continue
                else:
                    time.sleep(1)
                    continue

            data = response.json()

            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
                else:
                    st.session_state.last_error = "Empty AI response."
                    time.sleep(1)
                    continue

            if "error" in data:
                st.session_state.last_error = f"API error: {data['error']}"
                if "rate_limit" in str(data["error"]).lower():
                    time.sleep(2)
                    continue

            time.sleep(1)

        except requests.exceptions.Timeout:
            st.session_state.last_error = "Request timed out."
            time.sleep(1.5)
            continue
        except requests.exceptions.RequestException as e:
            st.session_state.last_error = f"Request error: {str(e)}"
            time.sleep(1.5)
            continue
        except ValueError as e:
            st.session_state.last_error = f"JSON parse error: {str(e)}"
            time.sleep(1.5)
            continue
        except Exception as e:
            st.session_state.last_error = f"Unexpected error: {str(e)}"
            time.sleep(1.5)
            continue

    return "⚠️ AI is still busy or failed to respond. Please click 'Home' and try again."

# --- SILO 2.5: SAFE PDF TEXT EXTRACTION ---
def extract_pdf_text(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)
        return "\n".join(pages_text).strip()
    except Exception as e:
        st.session_state.last_error = f"PDF read error: {str(e)}"
        return ""

# --- SILO 3: UI FLOW ---
if st.session_state.active_bid_text:
    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()

    doc = st.session_state.active_bid_text

    if st.session_state.analysis_mode == "Reporting":
        st.subheader("📊 Performance, Penalties & Stop-Clock Rules")

        if st.session_state.last_error:
            st.caption(f"Debug: {st.session_state.last_error}")

        if st.session_state.report_ans is None:
            prompt = "Explain: 1. HOW to report, 2. Uptime targets, 3. PENALTIES, 4. STOP-CLOCK conditions, 5. Monthly reports."
            with st.spinner("Analyzing contract reporting rules..."):
                st.session_state.report_ans = run_ai(doc, prompt, "Contract Compliance Expert. High Detail.")

        st.markdown(st.session_state.report_ans)

    else:
        # MOM-TEST BID VIEW
        if st.session_state.agency_name is None:
            with st.spinner("Finding agency, project name, and deadline..."):
                st.session_state.agency_name = run_ai(doc, "Agency Name?", "Return the agency name only.", "start")
                st.session_state.project_title = run_ai(doc, "Project Name?", "Return the project name only.", "start")
                st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Return the due date only.", "start")
            st.rerun()

        st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
        st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

        if st.session_state.last_error:
            st.caption(f"Debug: {st.session_state.last_error}")

        if st.session_state.summary_ans is None:
            with st.spinner("Building analysis..."):
                st.session_state.bid_details = run_ai(doc, "Find the solicitation ID, contact name, contact email, and key identifying details.", "Facts only.", "start")
                st.session_state.summary_ans = run_ai(doc, "What are the main project goals? Use simple bullets.", "Mom-test points.")
                st.session_state.tech_ans = run_ai(doc, "What technical tools, systems, or requirements are needed? Max 5 bullet points.", "List items.")
                st.session_state.submission_ans = run_ai(doc, "How do we apply or submit? Give a simple step-by-step list.", "1, 2, 3.", "start")
                st.session_state.compliance_ans = run_ai(doc, "What compliance, legal, insurance, licensing, or certification requirements are mentioned?", "Mom-test points.")
                st.session_state.award_ans = run_ai(doc, "How will the bid be evaluated or awarded?", "Simple list.")
            st.rerun()

        tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])

        with tabs[0]:
            st.markdown(st.session_state.bid_details if st.session_state.bid_details else "No details found.")

        with tabs[1]:
            st.info(st.session_state.summary_ans if st.session_state.summary_ans else "No summary found.")

        with tabs[2]:
            st.success(st.session_state.tech_ans if st.session_state.tech_ans else "No technical requirements found.")

        with tabs[3]:
            st.warning(st.session_state.submission_ans if st.session_state.submission_ans else "No submission steps found.")

        with tabs[4]:
            st.error(st.session_state.compliance_ans if st.session_state.compliance_ans else "No compliance details found.")

        with tabs[5]:
            st.write(st.session_state.award_ans if st.session_state.award_ans else "No award details found.")

else:
    st.title("🏛️ Public Sector Contract Analyzer")
    t1, t2, t3 = st.tabs(["📄 Bid Document", "📊 Contract Performance", "🔗 Agency URL"])

    with t1:
        up = st.file_uploader("Upload Bid PDF", type="pdf", key="m_bid")
        if up:
            extracted_text = extract_pdf_text(up)
            if extracted_text:
                st.session_state.active_bid_text = extracted_text
                st.session_state.analysis_mode = "Standard"
                reset_analysis()
                st.rerun()
            else:
                st.error("Could not read text from this PDF.")
                if st.session_state.last_error:
                    st.caption(f"Debug: {st.session_state.last_error}")

    with t2:
        up_c = st.file_uploader("Upload Contract PDF", type="pdf", key="m_sla")
        if up_c:
            extracted_text = extract_pdf_text(up_c)
            if extracted_text:
                st.session_state.active_bid_text = extracted_text
                st.session_state.analysis_mode = "Reporting"
                reset_analysis()
                st.rerun()
            else:
                st.error("Could not read text from this PDF.")
                if st.session_state.last_error:
                    st.caption(f"Debug: {st.session_state.last_error}")

    with t3:
        u_in = st.text_input("Agency URL:", placeholder="Paste link here...")
        if st.button("Scan Portal for IT"):
            pass  # Scraper logic remains safe
