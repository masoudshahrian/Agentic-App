"""Local Streamlit interface: pick one or two models, compare their answers, choose the better one.

Run with:  streamlit run ui.py
Each request is independent; the only state kept is the current screen (no storage, no API).
"""
from __future__ import annotations

import html

import streamlit as st

from app.compare import ModelResult, run_models
from app.graph import build_graph
from app.main import create_llm, run_request
from app.models import MODEL_CHOICES, choice_by_label
from app.utils.bidi import to_html

EXAMPLES = {
    "Calculate": "What is (3+56)+(2*2)?",
    "Translate (EN to FA)": "Translate to Persian: The meeting has been moved to Thursday afternoon.",
    "Persian to English": "این جمله را به انگلیسی ترجمه کن: جلسه به بعدازظهر پنجشنبه منتقل شد.",
    "Two skills": "Translate 'hello' to German and calculate 12*12",
    "Persian maths": "۱۵ درصد ۲۴۰ به علاوه ۷ چند می‌شود؟",
}
KIND_LABEL = {"answer": "Answer", "clarification": "Needs clarification", "unsupported": "Not supported", "error": "Error"}

st.set_page_config(page_title="I4Twins Agent", page_icon="🧠", layout="wide")
st.markdown(
    """<style>
    .block-container {max-width: 1180px; padding-top: 2.2rem;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; margin-bottom: 1.2rem; color: #fff;
           background: linear-gradient(120deg, #4f46e5 0%, #7c3aed 55%, #db2777 100%);}
    .hero h1 {margin: 0 0 .25rem 0; font-size: 1.9rem; color: #fff;}
    .hero p {margin: 0; opacity: .92; font-size: 1rem;}
    .card {border: 1px solid rgba(128,128,128,.28); border-radius: 14px; padding: 0; overflow: hidden;
           background: rgba(128,128,128,.05); margin-bottom: .6rem;}
    .card.chosen {border: 2px solid #16a34a; box-shadow: 0 0 0 3px rgba(22,163,74,.15);}
    .card-head {display: flex; justify-content: space-between; align-items: center; gap: .5rem;
                padding: .7rem 1rem; border-bottom: 1px solid rgba(128,128,128,.22); font-weight: 600;}
    .card-body {padding: 1rem 1.1rem; line-height: 1.95; font-size: 1.05rem; min-height: 90px;}
    .card-body .gap {height: .45rem;}
    .card-foot {display: flex; flex-wrap: wrap; gap: .4rem; padding: .6rem 1rem;
                border-top: 1px solid rgba(128,128,128,.22);}
    .pill {display: inline-block; padding: .12rem .6rem; border-radius: 999px; font-size: .78rem;
           background: rgba(79,70,229,.14); color: #6366f1; font-weight: 600;}
    .pill.grey {background: rgba(128,128,128,.16); color: inherit; font-weight: 500;}
    .pill.warn {background: rgba(217,119,6,.16); color: #d97706;}
    .pill.err {background: rgba(220,38,38,.16); color: #dc2626;}
    .pill.ok {background: rgba(22,163,74,.16); color: #16a34a;}
    </style>""",
    unsafe_allow_html=True,
)


def run_one(model_id: str, prompt: str):
    return run_request(build_graph(create_llm(model_id)), prompt)


def set_example(text: str) -> None:
    st.session_state["prompt"] = text


def label_of(model_id: str) -> str:
    return next((c.label for c in MODEL_CHOICES if c.model_id == model_id), model_id)


def card_html(result: ModelResult, chosen: bool) -> str:
    status_class = {"answer": "ok", "clarification": "warn", "unsupported": "warn", "error": "err"}[result.kind]
    pills = [f'<span class="pill {status_class}">{KIND_LABEL[result.kind]}</span>']
    if result.skills and result.kind != "error":
        pills.append(f'<span class="pill">{html.escape(result.skills)}</span>')
    if result.language:
        pills.append(f'<span class="pill grey">language: {html.escape(result.language)}</span>')
    pills.append(f'<span class="pill grey">{result.seconds}s</span>')
    badge = '<span class="pill ok">✓ Your choice</span>' if chosen else ""
    return (
        f'<div class="card{" chosen" if chosen else ""}">'
        f'<div class="card-head"><span>{html.escape(label_of(result.model_id))}</span>{badge}</div>'
        f'<div class="card-body">{to_html(result.answer)}</div>'
        f'<div class="card-foot">{"".join(pills)}</div></div>'
    )


# ---------------------------------------------------------------- header
st.markdown(
    '<div class="hero"><h1>🧠 I4Twins multi-skill agent</h1>'
    "<p>Summarize, translate, calculate or chat in English or Persian. Compare two models side by side and keep the better answer.</p></div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- model selection
labels = [c.label for c in MODEL_CHOICES]
mode = st.radio("Mode", ["One model", "Compare two models"], horizontal=True, label_visibility="collapsed")
if mode == "One model":
    selected = [st.selectbox("Model", labels, index=0)]
else:
    left, right = st.columns(2)
    first = left.selectbox("Model A", labels, index=0)
    second = right.selectbox("Model B", labels, index=min(2, len(labels) - 1))
    selected = [first, second]
st.caption(" · ".join(f"**{label}**: {choice_by_label(label).note}" for label in dict.fromkeys(selected)))
if len(set(selected)) < len(selected):
    st.info("Pick two different models to compare.")

# ---------------------------------------------------------------- input
st.markdown("**Try an example**")
for column, (name, text) in zip(st.columns(len(EXAMPLES)), EXAMPLES.items()):
    column.button(name, on_click=set_example, args=(text,), use_container_width=True)
prompt = st.text_area("Your request", key="prompt", height=120, placeholder="Write a request in English or Persian…")
ready = bool(prompt.strip()) and len(set(selected)) == len(selected)
if st.button("Run", type="primary", disabled=not ready, use_container_width=True):
    st.session_state.pop("chosen", None)
    with st.spinner("Thinking…"):
        st.session_state["results"] = run_models(prompt, [choice_by_label(l).model_id for l in selected], run_one)

# ---------------------------------------------------------------- results
results: list[ModelResult] = st.session_state.get("results", [])
if results:
    chosen = st.session_state.get("chosen") if len(results) > 1 else None
    st.divider()
    for column, (index, result) in zip(st.columns(len(results)), enumerate(results)):
        with column:
            st.markdown(card_html(result, chosen == index), unsafe_allow_html=True)
            if len(results) > 1 and result.kind != "error":
                if st.button("This answer is better", key=f"pick{index}", use_container_width=True,
                             type="primary" if chosen == index else "secondary"):
                    st.session_state["chosen"] = index
                    st.rerun()

with st.expander("How it works"):
    st.markdown(
        "A two-stage router first shortlists skills from compact metadata, then an LLM picks up to two. "
        "Only the selected skill's prompt is loaded. Calculations are done by a safe calculator, never by the model. "
        "Lines with Persian letters are right-aligned; English text and numbers are left-aligned."
    )
