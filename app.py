```python
import streamlit as st
import requests
from pypdf import PdfReader
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
        'report_ans': None
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
        'report_ans'
    ]:
        st.session_state[k] = None

# 🔥 STOP APP IF NO API KEY
if "GROQ_API_KEY" not in st.secrets:
    st.error("❌ GROQ_API_KEY missing. Go to Streamlit → Settings → Secrets")
    st.stop()

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- SILO 2: FIXED AI ENGINE ---
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

            if response.status_code == 401:
                return "❌ INVALID API KEY — Fix in Streamlit Secrets"

            if response.status_code == 429:
                time.sleep(2)
                continue

            if response.status_code != 200:
                return f"⚠️ API ERROR {response.status_code}: {response.text[:200]}"

            data = response.json()

            if "choices" in data and data["choices"]:
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content

            if "error" in data:
                return f"⚠️ API ERROR: {data['error']}"

        except requests.exceptions.Timeout:
            time.sleep(1.5)
            continue
        except requests.exceptions.RequestException as e:
            return f"⚠️ REQUEST ERROR: {str(e)}"
        except Exception as e:
            return f"⚠️ UNKNOWN ERROR: {str(e)}"

    return "⚠️ AI failed after retries. Click Home and try again."

# --- PDF SAFE EXTRACT ---
def extract_pdf_text(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = []
    for p in reader.pages:
        t = p.extract_text()
        if t:
            text.append(t)
    return "\n".join(text)

# --- UI FLOW ---
if st.session_state.active_bid_text:

    if st.button("🏠 Home / Back"):
        st.session_state.active_bid_text = None
        reset_analysis()
        st.rerun()

    doc = st.session_state.active_bid_text

    # HEADER LOAD
    if st.session_state.agency_name is None:
        st.session_state.agency_name = run_ai(doc, "Agency Name?", "Name only.", "start")
        st.session_state.project_title = run_ai(doc, "Project Name?", "Name only.", "start")
        st.session_state.detected_due_date = run_ai(doc, "Deadline?", "Date only.", "start")
        st.rerun()

    st.success(f"● STATUS: OPEN | 📅 DEADLINE: {st.session_state.detected_due_date}")
    st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name}")
    st.write(f"**📄 BID NAME:** {st.session_state.project_title}")

    # MAIN ANALYSIS
    if st.session_state.summary_ans is None:
        st.session_state.bid_details = run_ai(doc, "ID and Email.", "Facts only.", "start")
        st.session_state.summary_ans = run_ai(doc, "Simple goals?", "Mom-test points.")
        st.session_state.tech_ans = run_ai(doc, "Tools needed?", "List items.")
        st.session_state.submission_ans = run_ai(doc, "How to apply?", "1,2,3.", "start")
        st.session_state.compliance_ans = run_ai(doc, "Rules?", "Simple.")
        st.session_state.award_ans = run_ai(doc, "How to win?", "Simple.")
        st.rerun()

    tabs = st.tabs(["📋 Details", "📖 Plan", "🛠️ Tech", "📝 Apply", "⚖️ Legal", "💰 Award"])

    tabs[0].markdown(st.session_state.bid_details)
    tabs[1].info(st.session_state.summary_ans)
    tabs[2].success(st.session_state.tech_ans)
    tabs[3].warning(st.session_state.submission_ans)
    tabs[4].error(st.session_state.compliance_ans)
    tabs[5].write(st.session_state.award_ans)

else:
    st.title("🏛️ Public Sector Contract Analyzer")

    up = st.file_uploader("Upload Bid PDF", type="pdf")

    if up:
        text = extract_pdf_text(up)

        if text:
            st.session_state.active_bid_text = text
            reset_analysis()
            st.rerun()
        else:
            st.error("⚠️ Could not extract text from PDF")
```
