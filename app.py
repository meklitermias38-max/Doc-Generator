import html
import json
from typing import Any, Dict, List

import requests
import streamlit as st
from google import genai


st.set_page_config(page_title="KTTK Intelligence Platform", layout="wide")


# =========================
# PROMPTS
# =========================

BI_PROMPT = """
You are a senior enterprise strategy consultant.

Your task is to generate a complete Business Intelligence Report for the company below.

Company Name: {company_name}

The report must work for ANY company and must not be tailored only to Sony or any single example company.

STRICT RULES
- Identify 3 to 5 top business lines only
- Business lines must be based on products, services, or operating divisions
- Do NOT use geography-based business lines
- Use relevant competitors for each business line
- Keep the content commercially grounded and consulting-style
- If revenue is estimated, clearly indicate it is estimated
- Do NOT output markdown code fences
- Output clean, readable business report text
- Do not use markdown headings like ### or **

REPORT STRUCTURE

Title:
{company_name} Business Intelligence

SECTION 1 — BUSINESS LINE ANALYSIS

For EACH business line, use this exact structure:

1. [Business Line Name] ({company_name})

Revenue:
[Actual or estimated revenue. Clearly mark if estimated.]

Market Leaders:
[List 4 relevant market leaders]

What "Good" Looks Like Today in {company_name}:
[3 specific bullet points]

What “Good” Looks Like Today Across Market Leaders:

I. [Competitor 1]
[Give a benchmark label]
[Explain what makes this competitor a benchmark in this business line]

II. [Competitor 2]
[Give a benchmark label]
[Explain what makes this competitor a benchmark in this business line]

III. [Competitor 3]
[Give a benchmark label]
[Explain what makes this competitor a benchmark in this business line]

IV. [Competitor 4]
[Give a benchmark label]
[Explain what makes this competitor a benchmark in this business line]

Challenges faced by {company_name} in [Business Line Name]:
[3 challenge bullets tied to systems, agility, data, infrastructure, operating model, or modernization]

Strategic AI Reinvention and ROI

[Business Line Name]: [Short transformation theme]
[1 short paragraph on the transformation goal]

Tangible Value/ROI:
[1 quantified impact bullet]
[Second quantified impact bullet if relevant]

5 Daily AI-Driven Nudges:
1. [Specific nudge]
2. [Specific nudge]
3. [Specific nudge]
4. [Specific nudge]
5. [Specific nudge]

What to do to deliver:
[1 practical paragraph. Recommend an AI wrapper / control tower / intelligence layer approach where appropriate rather than immediate rip-and-replace]

SECTION 2 — SUMMARY OF QUANTIFIED IMPACT ANNUAL

At the end, provide a summary table with this exact structure:

Summary of Quantified Impact Annual

Business Unit
Primary Hard ROI Metrics
Annual Dollar Impact (Est. USD)

Include one row for each business line.

QUALITY BAR
- Make each business line feel specific to the company’s industry
- Use realistic competitor sets
- Use realistic ROI logic
- Keep the tone sharp, consulting-grade, and actionable
- Do not make the sections generic or repetitive
"""

LEADERSHIP_PROMPT = """
You are a senior executive intelligence analyst.

Your task is to generate a complete Leadership Mapping Report for the company below.

Company Name: {company_name}

Use the business intelligence below as context:
{bi_output}

Use the Apollo validation context below as a factual support layer.
Apollo validation context:
{apollo_context}

IMPORTANT RULES
- Apollo is a validation and enrichment source, not a reason to guess
- If Apollo data is weak, incomplete, or unclear, say Not Found rather than inventing
- Prefer current role accuracy over completeness
- Do NOT hallucinate LinkedIn URLs
- Keep the output readable and clearly sectioned
- Do not use markdown headings like ### or **

SECTION 1 — EXECUTIVE LEADERSHIP

Identify the current:
- CEO
- CFO
- CMO
- CIO or CTO if CIO does not exist

For EACH individual provide:
- Full Name
- Current Title
- Company
- LinkedIn profile URL if confidently available
- If uncertain, write Not Found

SECTION 2 — BUSINESS LINE LEADERSHIP

Identify the major business lines of the company.
For EACH business line provide:
1. Business Line Name
2. Global Head of Business Line
   - Full Name
   - Title
   - LinkedIn URL
3. Head of Technology for that Business Line
   - Full Name
   - Title
   - LinkedIn URL

SECTION 3 — INDEPENDENT BOARD MEMBERS

Provide 2 independent board members with strong industry relevance.

For EACH provide:
- Full Name
- Role
- Current or notable past role
- LinkedIn URL

FINAL INSTRUCTION
Use Apollo matches to strengthen confidence where possible, but never force a match.
"""

KTTK_PROMPT = """
You are a senior enterprise strategy advisor preparing executive-level meeting narratives.

Your task is to generate a KTTK-style Executive Intelligence Report.

Company Name: {company_name}

BUSINESS INTELLIGENCE:
{bi_output}

LEADERSHIP MAPPING:
{leadership_output}

STEP 0 — BUSINESS INTELLIGENCE SUMMARY
Create a structured Business Intelligence section that synthesizes all provided insights.

Structure:
1. Company Snapshot
2. Strategic Priorities
3. Operational Gaps
4. Technology and Data Gaps
5. Competitive Benchmarking
6. Financial Pressure Points
7. Transformation Opportunity Areas
8. Quantified Opportunity Range

STEP 1 — CEO STORYLINE
STEP 2 — CFO STORYLINE
STEP 3 — CMO STORYLINE
STEP 4 — CIO OR CTO STORYLINE
STEP 5 — BUSINESS LINE HEAD STORYLINES
STEP 6 — BUSINESS LINE TECH HEAD STORYLINES
STEP 7 — BOARD MEMBER STORYLINES

For each storyline include:
- The Hook
- Proof of Knowledge
- The Pivot
- The Close
- Value Proposition
- Detailed Meeting Structure
- ROI Framework
- Meeting Checklist

STRICT RULES
- All narratives must tie back to the Business Intelligence section
- Do not introduce totally new problems that were not grounded in BI
- Keep it executive-grade and consulting-style
- Keep the output readable with clear section headings
- Do not use markdown headings like ### or **
"""


# =========================
# APOLLO HELPERS
# =========================

APOLLO_BASE_URL = "https://api.apollo.io/api/v1"


def apollo_headers(api_key: str) -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Api-Key": api_key,
    }


def apollo_post(api_key: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(
        f"{APOLLO_BASE_URL}{endpoint}",
        headers=apollo_headers(api_key),
        json=payload,
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, dict) else {}


def apollo_search_organization(api_key: str, company_name: str) -> Dict[str, Any]:
    payload = {
        "q_organization_name": company_name,
        "page": 1,
        "per_page": 5,
    }
    data = apollo_post(api_key, "/mixed_companies/search", payload)
    accounts = data.get("accounts", []) or data.get("organizations", []) or []
    return accounts[0] if accounts else {}


def apollo_search_people(api_key: str, organization_id: str, title_keywords: List[str]) -> List[Dict[str, Any]]:
    payload = {
        "organization_ids": [organization_id],
        "person_titles": title_keywords,
        "page": 1,
        "per_page": 5,
    }
    data = apollo_post(api_key, "/mixed_people/api_search", payload)
    return data.get("people", []) or data.get("contacts", []) or []


def normalize_apollo_person(person: Dict[str, Any]) -> Dict[str, str]:
    return {
        "name": person.get("name") or "Not Found",
        "title": person.get("title") or "Not Found",
        "linkedin_url": person.get("linkedin_url") or "Not Found",
    }


def enrich_with_apollo(apollo_api_key: str, company_name: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "organization": {},
        "executives": {},
        "notes": [],
    }

    if not apollo_api_key.strip():
        result["notes"].append("Apollo API key not provided.")
        return result

    try:
        org = apollo_search_organization(apollo_api_key, company_name)
        org_id = org.get("id") or org.get("organization_id") or ""

        result["organization"] = {
            "name": org.get("name") or "",
            "domain": org.get("website_url") or org.get("primary_domain") or org.get("domain") or "",
            "apollo_id": org_id,
            "industry": org.get("industry") or "",
            "estimated_num_employees": org.get("estimated_num_employees") or "",
        }

        if not org_id:
            result["notes"].append("No matching Apollo organization ID found.")
            return result

        role_map = {
            "CEO": ["CEO", "Chief Executive Officer", "Chairman and CEO", "President and CEO"],
            "CFO": ["CFO", "Chief Financial Officer"],
            "CMO": ["CMO", "Chief Marketing Officer", "Chief Brand Officer"],
            "CIO_CTO": ["CIO", "Chief Information Officer", "CTO", "Chief Technology Officer"],
        }

        for role_name, titles in role_map.items():
            people = apollo_search_people(apollo_api_key, org_id, titles)
            result["executives"][role_name] = [normalize_apollo_person(p) for p in people]

        result["notes"].append("Apollo validation completed.")
        return result

    except Exception as e:
        result["notes"].append(f"Apollo validation error: {e}")
        return result


# =========================
# GEMINI CALL
# =========================

def call_gemini_llm(
    gemini_api_key: str,
    gemini_model: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    client = genai.Client(api_key=gemini_api_key)
    response = client.models.generate_content(
        model=gemini_model,
        contents=f"{system_prompt}\n\n{user_prompt}",
    )
    return response.text or ""


# =========================
# HTML GENERATOR
# =========================

def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def build_kttk_html(company_name: str, bi_output: str, leadership_output: str, kttk_output: str) -> str:
    company = safe_text(company_name)
    bi = safe_text(bi_output).replace("\n", "<br>")
    leadership = safe_text(leadership_output).replace("\n", "<br>")
    kttk = safe_text(kttk_output).replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{company} Strategic Hub</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            font-family: Arial, sans-serif;
            background: #f5f5f5;
            color: #111827;
        }}
        .shell {{
            display: grid;
            grid-template-columns: 260px 1fr;
            min-height: 100vh;
        }}
        .sidebar {{
            background: #0f172a;
            color: white;
            padding: 28px 20px;
        }}
        .sidebar h1 {{
            font-size: 24px;
            margin: 0;
        }}
        .sidebar p {{
            margin-top: 8px;
            color: #94a3b8;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-weight: bold;
        }}
        .nav-item {{
            margin-top: 14px;
            padding: 12px 14px;
            border-radius: 10px;
            background: #1e293b;
            font-weight: bold;
            font-size: 14px;
        }}
        .main {{
            padding: 36px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 20px;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }}
        .badge {{
            display: inline-block;
            background: #2563eb;
            color: white;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: bold;
        }}
        .header h2 {{
            margin: 10px 0 0 0;
            font-size: 36px;
        }}
        .header-card {{
            background: white;
            border-radius: 14px;
            padding: 18px 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border: 1px solid #e5e7eb;
        }}
        .section {{
            background: white;
            padding: 24px;
            margin-bottom: 20px;
            border-radius: 14px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            border: 1px solid #e5e7eb;
        }}
        .section h3 {{
            margin-top: 0;
            font-size: 22px;
        }}
        .report-content {{
            line-height: 1.7;
            word-break: break-word;
            font-size: 14px;
        }}
        @media (max-width: 900px) {{
            .shell {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="shell">
        <aside class="sidebar">
            <h1>{company}</h1>
            <p>Strategic Analysis</p>
            <div class="nav-item">Business Intelligence</div>
            <div class="nav-item">Leadership Mapping</div>
            <div class="nav-item">KTTK</div>
        </aside>

        <main class="main">
            <div class="header">
                <div>
                    <span class="badge">Confidential</span>
                    <h2>{company} Executive Strategic Hub</h2>
                </div>
                <div class="header-card">
                    <div><strong>Lead Advisor:</strong> Avi Vashistha</div>
                    <div><strong>Target Account:</strong> {company}</div>
                </div>
            </div>

            <div class="section">
                <h3>Business Intelligence</h3>
                <div class="report-content">{bi}</div>
            </div>

            <div class="section">
                <h3>Leadership Mapping</h3>
                <div class="report-content">{leadership}</div>
            </div>

            <div class="section">
                <h3>KTTK Output</h3>
                <div class="report-content">{kttk}</div>
            </div>
        </main>
    </div>
</body>
</html>
"""


def save_html_file(company_name: str, html_content: str) -> str:
    safe_name = company_name.replace(" ", "_").replace("/", "_")
    filename = f"{safe_name}_report.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename


# =========================
# RUNNERS
# =========================

def run_bi(gemini_api_key: str, gemini_model: str, company_name: str) -> Dict[str, str]:
    system_prompt = "You are a precise enterprise strategy analyst. Follow the required structure exactly."
    user_prompt = BI_PROMPT.format(company_name=company_name)
    raw = call_gemini_llm(gemini_api_key, gemini_model, system_prompt, user_prompt)
    return {"raw_output": raw}


def run_leadership(
    gemini_api_key: str,
    gemini_model: str,
    company_name: str,
    bi_data: Dict[str, str],
    apollo_data: Dict[str, Any],
) -> Dict[str, str]:
    system_prompt = "You are a precise executive intelligence analyst. Follow the required structure exactly."
    user_prompt = LEADERSHIP_PROMPT.format(
        company_name=company_name,
        bi_output=bi_data.get("raw_output", ""),
        apollo_context=json.dumps(apollo_data, indent=2),
    )
    raw = call_gemini_llm(gemini_api_key, gemini_model, system_prompt, user_prompt)
    return {"raw_output": raw}


def run_kttk(
    gemini_api_key: str,
    gemini_model: str,
    company_name: str,
    bi_data: Dict[str, str],
    leadership_data: Dict[str, str],
) -> Dict[str, str]:
    system_prompt = "You are a precise strategy narrative generator. Follow the required structure exactly."
    user_prompt = KTTK_PROMPT.format(
        company_name=company_name,
        bi_output=bi_data.get("raw_output", ""),
        leadership_output=leadership_data.get("raw_output", ""),
    )
    raw = call_gemini_llm(gemini_api_key, gemini_model, system_prompt, user_prompt)
    return {"raw_output": raw}


# =========================
# SESSION STATE
# =========================

if "bi_data" not in st.session_state:
    st.session_state.bi_data = None
if "leadership_data" not in st.session_state:
    st.session_state.leadership_data = None
if "apollo_data" not in st.session_state:
    st.session_state.apollo_data = None
if "kttk_data" not in st.session_state:
    st.session_state.kttk_data = None
if "html_output" not in st.session_state:
    st.session_state.html_output = None
if "html_filename" not in st.session_state:
    st.session_state.html_filename = None


# =========================
# SIDEBAR
# =========================

with st.sidebar:
    st.header("Gemini Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password")
    gemini_model = st.text_input("Model", value="gemini-2.5-flash")
    st.caption("Recommended starting model: gemini-2.5-flash")

    st.divider()

    st.header("Apollo Settings")
    apollo_api_key = st.text_input("Apollo API Key (optional)", type="password")
    st.caption("Used to validate and enrich leadership mapping.")


# =========================
# MAIN UI
# =========================

st.title("KTTK Intelligence Platform")

company_name = st.text_input("Company Name", placeholder="e.g. Sony Group Corporation")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Run Business Intelligence", use_container_width=True):
        if not company_name or not gemini_api_key:
            st.error("Enter a company name and Gemini API key.")
        else:
            with st.spinner("Generating Business Intelligence..."):
                try:
                    st.session_state.bi_data = run_bi(gemini_api_key, gemini_model, company_name)
                    st.success("Business Intelligence complete.")
                except Exception as e:
                    st.error(f"BI failed: {e}")

with col2:
    if st.button("Run Leadership Mapping", use_container_width=True):
        if not st.session_state.bi_data:
            st.error("Run Business Intelligence first.")
        elif not gemini_api_key:
            st.error("Enter a Gemini API key.")
        else:
            with st.spinner("Running Leadership Mapping with Apollo validation..."):
                try:
                    st.session_state.apollo_data = enrich_with_apollo(apollo_api_key, company_name)

                    st.session_state.leadership_data = run_leadership(
                        gemini_api_key,
                        gemini_model,
                        company_name,
                        st.session_state.bi_data,
                        st.session_state.apollo_data,
                    )

                    st.success("Leadership Mapping complete with Apollo validation layer.")
                except Exception as e:
                    st.error(f"Leadership Mapping failed: {e}")

with col3:
    if st.button("Run KTTK", use_container_width=True):
        if not st.session_state.bi_data or not st.session_state.leadership_data:
            st.error("Run Business Intelligence and Leadership Mapping first.")
        elif not gemini_api_key:
            st.error("Enter a Gemini API key.")
        else:
            with st.spinner("Generating KTTK..."):
                try:
                    st.session_state.kttk_data = run_kttk(
                        gemini_api_key,
                        gemini_model,
                        company_name,
                        st.session_state.bi_data,
                        st.session_state.leadership_data,
                    )
                    st.success("KTTK complete.")
                except Exception as e:
                    st.error(f"KTTK failed: {e}")

with col4:
    if st.button("Generate HTML", use_container_width=True):
        if not st.session_state.bi_data or not st.session_state.leadership_data or not st.session_state.kttk_data:
            st.error("Run Business Intelligence, Leadership Mapping, and KTTK first.")
        else:
            try:
                html_content = build_kttk_html(
                    company_name,
                    st.session_state.bi_data["raw_output"],
                    st.session_state.leadership_data["raw_output"],
                    st.session_state.kttk_data["raw_output"],
                )
                filename = save_html_file(company_name, html_content)
                st.session_state.html_output = html_content
                st.session_state.html_filename = filename
                st.success(f"Saved: {filename}")
            except Exception as e:
                st.error(f"HTML generation failed: {e}")


tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Business Intelligence", "Leadership Mapping", "Apollo Validation", "KTTK", "HTML Export"]
)

with tab1:
    st.subheader("Business Intelligence Output")
    if st.session_state.bi_data:
        st.text_area(
            "BI Report",
            st.session_state.bi_data["raw_output"],
            height=550
        )
    else:
        st.info("No BI output yet.")

with tab2:
    st.subheader("Leadership Mapping Output")
    if st.session_state.leadership_data:
        st.text_area(
            "Leadership Report",
            st.session_state.leadership_data["raw_output"],
            height=550
        )
    else:
        st.info("No leadership output yet.")

with tab3:
    st.subheader("Apollo Validation Layer")
    if st.session_state.apollo_data:
        org = st.session_state.apollo_data.get("organization", {})
        execs = st.session_state.apollo_data.get("executives", {})
        notes = st.session_state.apollo_data.get("notes", [])

        if org:
            st.markdown("**Organization Match**")
            st.json(org)

        if execs:
            st.markdown("**Executive Validation Candidates**")
            st.json(execs)

        if notes:
            st.markdown("**Validation Notes**")
            for note in notes:
                st.write(f"- {note}")
    else:
        st.info("No Apollo validation data yet. Run Leadership Mapping first.")

with tab4:
    st.subheader("KTTK Output")
    if st.session_state.kttk_data:
        st.text_area(
            "KTTK Report",
            st.session_state.kttk_data["raw_output"],
            height=550
        )
    else:
        st.info("No KTTK output yet.")

with tab5:
    st.subheader("HTML Export")
    if st.session_state.bi_data and st.session_state.leadership_data and st.session_state.kttk_data:
        html_content = build_kttk_html(
            company_name,
            st.session_state.bi_data["raw_output"],
            st.session_state.leadership_data["raw_output"],
            st.session_state.kttk_data["raw_output"],
        )

        st.download_button(
            label="Download HTML Report",
            data=html_content,
            file_name=f"{company_name.replace(' ', '_')}_report.html",
            mime="text/html",
        )
        st.info("Download the HTML file and open it in your browser.")
    else:
        st.warning("Run BI, Leadership, and KTTK first.")