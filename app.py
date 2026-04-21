import streamlit as st
import requests
import time

# -----------------------------
# 1. SESSION STATE SETUP
# -----------------------------
def init_vault():
    defaults = {
        "active_bid_text": None,
        "agency_name": None,
        "project_title": None,
        "summary_ans": None,
        "tech_ans": None,
        "apply_ans": None,
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_vault()

def hard_reset():
    for key in [
        "agency_name",
        "project_title",
        "summary_ans",
        "tech_ans",
        "apply_ans",
        "last_error",
    ]:
        st.session_state[key] = None

# -----------------------------
# 2. API CONFIG
# -----------------------------
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
API_URL = "https://api.groq.com/openai/v1/chat/completions"

# -----------------------------
# 3. AI CALL FUNCTION
# -----------------------------
def call_ai(text, prompt, max_chars=12000):
    """Call Groq API with retries and visible error handling."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Use simple words. Mom-test style."
            },
            {
                "role": "user",
                "content": f"{prompt}\n\nTEXT:\n{text[:max_chars]}"
            }
        ],
        "temperature": 0.0,
    }

    last_err = None

    for attempt in range(3):
        try:
            time.sleep(1.2)
            r = requests.post(API_URL, headers=headers, json=payload, timeout=25)
            r.raise_for_status()

            res = r.json()

            if "choices" not in res or not res["choices"]:
                last_err = f"No choices returned. Response: {res}"
                continue

            content = res["choices"][0]["message"]["content"].strip()

            if len(content) > 5:
                return content

            last_err = "AI returned an empty or too-short response."

        except requests.exceptions.RequestException as e:
            last_err = f"HTTP/API error: {e}"
        except ValueError as e:
            last_err = f"JSON parse error: {e}"
        except Exception as e:
            last_err = f"Unexpected error: {e}"

    st.session_state.last_error = last_err
    return None

# -----------------------------
# 4. HELPER FUNCTIONS
# -----------------------------
def ensure_basic_fields(doc):
    """Only fill agency/project once. No rerun needed."""
    if st.session_state.agency_name is None:
        with st.spinner("🔍 Locating Agency..."):
            st.session_state.agency_name = call_ai(doc, "What is the Agency Name? Return only the agency name.")

    if st.session_state.project_title is None:
        with st.spinner("📄 Identifying Project..."):
            st.session_state.project_title = call_ai(doc, "What is the Project Title? Return only the project title.")

def generate_summary(doc):
    if st.session_state.summary_ans is None:
        with st.spinner("Simplifying plan..."):
            st.session_state.summary_ans = call_ai(
                doc,
                "What are the project goals? Explain in simple words using short bullet points."
            )

def generate_tech(doc):
    if st.session_state.tech_ans is None:
        with st.spinner("Reviewing technical requirements..."):
            st.session_state.tech_ans = call_ai(
                doc,
                "What are the technical requirements or important scope items? Use simple bullet points."
            )

def generate_apply(doc):
    if st.session_state.apply_ans is None:
        with st.spinner("Finding application requirements..."):
            st.session_state.apply_ans = call_ai(
                doc,
                "What does the applicant need to submit or do to apply? Use a simple checklist."
            )

# -----------------------------
# 5. DEMO INPUT IF NO DOC LOADED
# -----------------------------
st.title("Bid Analyzer")

if st.session_state.active_bid_text is None:
    st.info("Paste bid text below to test.")
    sample_text = st.text_area("Bid / RFP Text", height=250)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Analyze"):
            if sample_text.strip():
                st.session_state.active_bid_text = sample_text.strip()
                hard_reset()
                st.rerun()
            else:
                st.warning("Please paste bid text first.")

    with col2:
        if st.button("Clear"):
            st.session_state.active_bid_text = None
            hard_reset()
            st.rerun()

else:
    # -----------------------------
    # 6. MAIN ANALYSIS VIEW
    # -----------------------------
    if st.button("🏠 Exit Analysis"):
        st.session_state.active_bid_text = None
        hard_reset()
        st.rerun()

    doc = st.session_state.active_bid_text

    ensure_basic_fields(doc)

    if st.session_state.agency_name or st.session_state.project_title:
        st.success("✅ ANALYSIS READY")
        st.write(f"**🏛️ AGENCY:** {st.session_state.agency_name or 'Not found'}")
        st.write(f"**📄 BID:** {st.session_state.project_title or 'Not found'}")

    if st.session_state.last_error:
        st.error(f"Last API error: {st.session_state.last_error}")

    t1, t2, t3 = st.tabs(["📖 Plan", "🛠️ Tech", "📝 Apply"])

    with t1:
        if st.session_state.summary_ans is None:
            if st.button("Generate Plan Summary"):
                generate_summary(doc)

        if st.session_state.summary_ans:
            st.markdown(st.session_state.summary_ans)

    with t2:
        if st.session_state.tech_ans is None:
            if st.button("Generate Tech Review"):
                generate_tech(doc)

        if st.session_state.tech_ans:
            st.markdown(st.session_state.tech_ans)

    with t3:
        if st.session_state.apply_ans is None:
            if st.button("Generate Apply Checklist"):
                generate_apply(doc)

        if st.session_state.apply_ans:
            st.markdown(st.session_state.apply_ans)
