"""
Streamlit Dashboard for Fail-Closed Decision Gate

Runs locally, in Colab, or anywhere Streamlit is supported.
No external services. No databases. Deterministic.
"""

import streamlit as st
import json
from gate import VerificationGate, Decision


st.set_page_config(
    page_title="Fail-Closed Verification Gate",
    layout="wide"
)

st.title("🛡️ Fail-Closed Verification Gate")
st.caption("Deterministic evidence-based auditing for AI outputs.")


# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    min_support = st.number_input(
        "Minimum evidence support per claim",
        min_value=1,
        max_value=10,
        value=2,
        step=1
    )
    st.markdown(
        """
        **Decision rules**
        - BLOCK: no evidence or zero supported claims
        - ESCALATE: support < threshold
        - ALLOW: support ≥ threshold
        """
    )


gate = VerificationGate(min_support=min_support)


# --- Main layout ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Claims / Output")
    claims_text = st.text_area(
        "Paste AI output or factual claims:",
        height=220,
        placeholder="The sky is blue. Data is encrypted."
    )

with col2:
    st.subheader("2. Evidence")
    uploads = st.file_uploader(
        "Upload evidence files (.txt or .json)",
        accept_multiple_files=True
    )

    evidence = []
    if uploads:
        for f in uploads:
            content = f.read().decode("utf-8")
            if f.name.endswith(".json"):
                evidence.extend(json.loads(content))
            else:
                evidence.append({"id": f.name, "content": content})
        st.success(f"{len(evidence)} evidence items loaded.")


# --- Execute ---
st.divider()

if st.button("Run Verification", use_container_width=True):
    if not claims_text or not evidence:
        st.error("Both claims and evidence are required.")
    else:
        result = gate.verify(claims_text, evidence)

        color = {
            Decision.ALLOW: "green",
            Decision.BLOCK: "red",
            Decision.ESCALATE: "orange",
        }[result.decision]

        st.markdown(f"## Result: :{color}[{result.decision.value}]")

        for r in result.reasons:
            st.write(f"• {r}")

        st.subheader("Audit Details")
        rows = []
        supports = result.meta.get("supports", {})

        for claim, count in supports.items():
            rows.append({
                "Claim": claim,
                "Support Count": count
            })

        if rows:
            st.table(rows)

        st.caption(f"Trace ID: {result.trace_id}")


# --- Footer ---
st.markdown(
    """
    ---
    **Properties**
    - Zero LLM dependencies
    - Fully local execution
    - Deterministic + auditable
    """
)
