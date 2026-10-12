"""Review one claim at a time. Verification logic lives in core.pipeline."""
import sys
from html import escape
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import streamlit as st
from core.input_handler import prepare_input
from core.schemas import VerifyRequest
from core.pipeline import verify
from core.claim_extractor import extract_claims
from app.visuals import scanning_html, result_html, evidence_heading_html, evidence_card_html, empty_evidence_html

st.set_page_config(page_title="VeriForward · Check before you share", page_icon="🔎", layout="wide")
st.html((Path(__file__).parent / "styles.css").read_text(encoding="utf-8"))


def reset_review():
    for key in ("prepared", "result", "reviewed", "corrected", "selected", "last_selected", "original"):
        st.session_state.pop(key, None)


def use_example():
    reset_review()
    st.session_state.forward_text = "Drinking hot water prevents viral infections."


def section_label(number, title):
    st.html(f'<div class="section-label"><span>{number}</span>{escape(title)}</div>')


st.html('''
<div class="topbar">
 <div class="brand"><span class="brand-mark">V↗</span>VeriForward<span class="brand-tag">EVIDENCE FIRST</span></div>
 <div class="topbar-note"><span class="status-dot"></span>Think critically. Share responsibly.</div>
</div>
<section class="hero">
 <div class="hero-copy">
  <div class="eyebrow">A LITTLE PAUSE. A BETTER FORWARD.</div>
  <h1>Before you share,<br><span>check what’s there.</span></h1>
  <p>Turn a questionable forward into a thoughtful reply.<br>Review the claim, explore the evidence, and decide what to share.</p>
  <div class="hero-tags"><span>↗ Source-linked evidence</span><span>◎ You review the claim</span><span>↳ A reply you can copy</span></div>
 </div>
 <div class="hero-art" aria-hidden="true">
  <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div>
  <div class="message-card"><span class="message-avatar">↗</span><div><small>FORWARDED MESSAGE</small><div class="message-line"></div><div class="message-line short"></div></div><span class="question-mark">?</span></div>
  <div class="evidence-stamp"><span>⌕</span><div>Follow the evidence<small>Every claim deserves a closer look.</small></div></div>
  <span class="art-spark spark-one">✳</span><span class="art-spark spark-two">+</span>
 </div>
</section>
''')
prepared = "prepared" in st.session_state
completed = "result" in st.session_state
st.html(f'''
<div class="workflow" aria-label="Verification workflow">
 <div class="workflow-step {'done' if prepared else 'active'}"><span>{'✓' if prepared else '01'}</span><div>Add your input<small>Text, a link, or a screenshot</small></div></div>
 <div class="workflow-step {'done' if completed else 'active' if prepared else ''}"><span>{'✓' if completed else '02'}</span><div>Review the claim<small>Choose exactly what to check</small></div></div>
 <div class="workflow-step {'active' if completed else ''}"><span>03</span><div>Explore the evidence<small>Read the result and sources</small></div></div>
</div>
''')
main, aside = st.columns([2.25, 1], gap="large")
with main:
    with st.container(border=True):
        section_label("01", "What would you like to check?")
        st.caption("Start with the message that made you pause.")
        kind = st.radio("Choose your input", ["text", "url", "image"], horizontal=True, format_func=lambda v: {"text": "✎  Paste text", "url": "↗  Article link", "image": "▧  Screenshot"}[v], label_visibility="collapsed")
        if st.session_state.get("kind") != kind:
            reset_review()
            st.session_state.kind = kind
        if kind == "image":
            upload = st.file_uploader("Drop your screenshot here", type=["png", "jpg", "jpeg", "webp"])
            st.caption("PNG, JPG, or WebP · Maximum 5 MB · English text")
            content = upload.getvalue() if upload else None
        elif kind == "url":
            content = st.text_input("Publisher article URL", placeholder="https://publisher.com/article", max_chars=20000)
            st.caption("A direct link to the original publisher works best.")
        else:
            content = st.text_area("English claim or forward", key="forward_text", height=170, max_chars=20000, placeholder="Paste a WhatsApp forward, a Facebook post, or a claim you want to investigate…", label_visibility="collapsed")
            st.caption(f"{len(content):,} / 20,000 characters · English text")
        if st.button("Prepare for review  →", type="primary", disabled=not content or (isinstance(content, str) and not content.strip()), use_container_width=True):
            try:
                with st.spinner("Preparing your input…"):
                    prepared_input = prepare_input(kind, content)
                    reset_review()
                    st.session_state.prepared = prepared_input
                    st.session_state.original = content if kind != "image" else "[screenshot; bytes not retained]"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    if "prepared" in st.session_state:
        with st.container(border=True):
            section_label("02", "Make the claim your own")
            st.caption("Check the extracted wording, then choose one claim to investigate.")
            corrected = st.text_area("Review and correct extracted text", value=st.session_state.prepared["extracted_text"], key="corrected", max_chars=20000)
            candidates = extract_claims(corrected)
            if candidates:
                selected = st.selectbox("Choose one sentence or claim", candidates, key="selected")
                if st.session_state.get("last_selected") != selected:
                    st.session_state.reviewed = selected[:1500]
                    st.session_state.last_selected = selected
                claim = st.text_area("Edit the single claim to check", key="reviewed", max_chars=1500)
                st.caption("Keep names, negation, dates, and quantities. Split compound claims manually; ambiguous dates and locations stay unresolved.")
                if st.button("Investigate this claim  ↗", type="primary", disabled=not claim.strip(), use_container_width=True):
                    status = st.empty()
                    st.session_state.pop("result", None)
                    try:
                        status.html(scanning_html())
                        st.session_state.result = verify(VerifyRequest(input_type="url" if kind == "url" else "text", content=st.session_state.original if kind != "image" else corrected, reviewed_claim=claim), progress=lambda message: status.html(scanning_html(message)))
                        status.empty()
                        st.rerun()
                    except Exception as exc:
                        status.empty()
                        st.error(f"System error: {exc}")
            else:
                st.info("Add a complete sentence above to select a claim.")
with aside:
    st.html('''
    <div class="guide-card"><div class="eyebrow">YOUR QUICK GUIDE</div><h3>A claim is a starting point.<br>Evidence is the next step.</h3>
     <div class="guide-item"><span>01</span><div><b>Bring the original wording</b><p>Keep names, dates, and numbers. Small details can change a claim.</p></div></div>
     <div class="guide-item"><span>02</span><div><b>Focus on one statement</b><p>Review and edit a single claim before checking it.</p></div></div>
     <div class="guide-item"><span>03</span><div><b>Read beyond the verdict</b><p>Explore linked sources and limitations before sharing a reply.</p></div></div>
    </div>
    <div class="honesty-card"><span>◎</span><div><b>“Not enough evidence” is a useful answer.</b><p>Missing evidence does not make a claim false. This English MVP may return an inconclusive result.</p></div></div>
    ''')
    if kind == "text":
        with st.container(border=True):
            st.markdown("**Need a starting point?**")
            st.caption("Try a sample claim to explore the review process. The result will depend on retrieved evidence.")
            st.button("Try a sample claim  ↗", on_click=use_example, use_container_width=True)
if "result" in st.session_state:
    result = st.session_state.result
    st.divider()
    section_label("03", "Here’s what the evidence says")
    st.html(result_html(result))
    st.caption(f"Checked: {result.verification_timestamp}")
    evidence_columns = st.columns(2, gap="large")
    for column, label, evidence, tone in ((evidence_columns[0], "Supporting passages", result.supporting_evidence, "support"), (evidence_columns[1], "Contradicting passages", result.contradicting_evidence, "contradict")):
        with column:
            st.html(evidence_heading_html(label, len(evidence), tone))
            if not evidence:
                st.html(empty_evidence_html(tone))
            for index, item in enumerate(evidence, start=1):
                st.html(evidence_card_html(item, index, tone))
    with st.expander("Explore related coverage and extraction status"):
        if not result.related_articles:
            st.caption("No related articles were retrieved.")
        for article in result.related_articles:
            with st.container(border=True):
                st.write(article.title)
                st.link_button("Open source ↗", article.publisher_url or article.link)
                st.caption(f"{article.source} · Published: {article.published or 'unknown'} · {article.extraction_status}")
    with st.expander("Read limitations and failures", expanded=bool(result.failures)):
        for message in result.warnings + result.failures:
            st.write(message)
        for item in result.assessed_evidence:
            for message in item.context_warnings:
                st.write(message)
    with st.container(border=True):
        st.html('<div class="reply-heading"><span>↳</span><div><div class="eyebrow">FROM CHECKING TO SHARING</div><h3>A thoughtful reply, ready to share</h3></div></div>')
        st.caption("Use the copy button in the top-right corner of the reply. Review the wording before sending.")
        st.code(result.whatsapp_reply, language=None)
        st.download_button("Download evidence snapshot  ↓", result.model_dump_json(indent=2), file_name="veriforward-evidence.json", mime="application/json")
st.html('<div class="footer"><b>VeriForward</b><span>Pause. Check. Then share.</span><span>English MVP · Evidence has limits.</span></div>')
