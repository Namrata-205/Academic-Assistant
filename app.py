"""NCERT bilingual prerequisite KG explorer.
Run: streamlit run app.py
Place extracted files under assets/ncert_knowledge_graph/.
"""
from pathlib import Path
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="NCERT Bilingual Knowledge Graph", page_icon="📚", layout="wide")
BASE = Path(__file__).resolve().parent
DATA = BASE / "assets" / "NCERT_Knowledge_Graph"
from diagnostic.engine import graph_source_path, load_graph_rows
CSV = graph_source_path()

st.markdown("""<style>
[data-testid="stAppViewContainer"]{background:#080f20;color:#e5edf9}
[data-testid="stSidebar"]{background:#101a30;border-right:1px solid #263550}
[data-testid="stHeader"]{background:transparent}
.block-container{padding:1.3rem 2rem;max-width:1900px}h1{font-size:2rem!important}.atlas-summary{display:flex;gap:28px;align-items:center;padding:12px 4px;color:#9fb2ce;font-size:13px}.atlas-summary b{color:#edf5ff}.atlas-live{margin-left:auto;color:#58ddcc;font-size:10px;letter-spacing:.15em}
h1,h2,h3{color:#f1f5ff!important;letter-spacing:-.035em}
[data-testid="stMetric"]{background:#111e35;border:1px solid #293954;border-radius:16px;padding:16px 22px}
[data-testid="stMetricLabel"], [data-testid="stCaptionContainer"]{color:#9fb2ce}
</style><div style="color:#58ddcc;font-size:12px;letter-spacing:.22em;font-weight:700">NCERT / CONCEPT ATLAS</div>""", unsafe_allow_html=True)
st.title("Concept Atlas")
st.caption("Class 6 Mathematics · Chapters 1–3 · Proposed prerequisite relationships (not yet academically validated)")

if not CSV.exists():
    st.error(f"Missing file: {CSV}")
    st.info("Extract your downloaded ZIP into assets/ncert_knowledge_graph/ so prerequisite_edges.csv exists there.")
    st.stop()

@st.cache_data

def load_data(path: str, modified: float):
    return pd.DataFrame(load_graph_rows(path))

df = load_data(str(CSV), CSV.stat().st_mtime)
needed = {"source_id", "target_id", "source_en", "source_hi", "target_en", "target_hi"}
if not needed.issubset(df.columns):
    st.error(f"Missing CSV columns: {', '.join(sorted(needed - set(df.columns)))}")
    st.stop()

nodes = {}
edges = []
for _, r in df.iterrows():
    a, b = r["source_id"].strip(), r["target_id"].strip()
    if not a or not b:
        continue
    for key, prefix in [(a, "source"), (b, "target")]:
        candidate = {
            "id": key,
            "en": r.get(f"{prefix}_en", "").strip() or key,
            "hi": r.get(f"{prefix}_hi", "").strip(),
            "chapter": r.get(f"{prefix}_chapter", "").strip().upper(),
        }
        if key not in nodes:
            nodes[key] = candidate
        else:
            for field in ("en", "hi", "chapter"):
                if not nodes[key].get(field):
                    nodes[key][field] = candidate[field]
    edges.append({
        "id": f"e{len(edges)}", "source": a, "target": b,
        "reasoning": r.get("reasoning", ""),
        "confidence": r.get("confidence", ""),
        "evidence": r.get("supporting_passage_ids", ""),
        "status": r.get("validation_status", "Unreviewed"),
        "cycle": str(r.get("cycle_flag", "")).strip().lower() in ("true", "1", "yes"),
    })

workspace = st.radio("Workspace", ["3D Graph", "Diagnostic", "Review & pilot"], horizontal=True)
if workspace == "Diagnostic":
    from diagnostic.ui import render_diagnostic
    render_diagnostic()
    st.stop()
if workspace == "Review & pilot":
    from diagnostic.ui import render_review
    render_review()
    st.stop()

chapters = sorted({n["chapter"] for n in nodes.values() if n["chapter"]})
with st.expander("Explore settings", expanded=False):
    filters = st.columns([2, 2, 2, 1.5])
    with filters[0]:
        selected_chapters = st.multiselect("Chapters", chapters, default=chapters)
    with filters[1]:
        mode = st.radio("Graph view", ["Focus on a concept", "Full graph"], index=1, horizontal=True)
    with filters[2]:
        labels = st.selectbox("Node labels", ["English + Hindi", "English only", "Hindi only"])
    with filters[3]:
        depth = st.slider("Traversal depth", 1, 3, 1, disabled=mode == "Full graph")

choices = sorted(nodes.values(), key=lambda n: (n["en"].lower(), n["id"]))
allowed = [n for n in choices if n["chapter"] in selected_chapters]
if not allowed:
    st.warning("Select at least one chapter containing concepts.")
    st.stop()

chosen = st.selectbox(
    "Select a concept (English / हिंदी)",
    options=[n["id"] for n in allowed],
    format_func=lambda i: f"{nodes[i]['en']} — {nodes[i]['hi']} [{nodes[i]['chapter']}]",
)

visible_nodes = {n["id"] for n in allowed}
visible_edges = [e for e in edges if e["source"] in visible_nodes and e["target"] in visible_nodes]
if mode == "Focus on a concept":
    neighbors = {chosen}
    for _ in range(depth):
        neighbors |= {e["source"] for e in visible_edges if e["target"] in neighbors}
        neighbors |= {e["target"] for e in visible_edges if e["source"] in neighbors}
    visible_nodes &= neighbors
    visible_edges = [e for e in visible_edges if e["source"] in visible_nodes and e["target"] in visible_nodes]

st.markdown(
    f'<div class="atlas-summary"><span><b>{len(visible_nodes)}</b> concepts</span>'
    f'<span><b>{len(visible_edges)}</b> visible connections</span>'
    f'<span><b>{len(edges)}</b> total relationships</span>'
    '<span class="atlas-live">3D EXPLORER</span></div>', unsafe_allow_html=True,
)

payload = {
    "nodes": [nodes[n] for n in sorted(visible_nodes)],
    "edges": visible_edges,
    "selected": chosen,
    "labels": labels,
    "focus": mode == "Focus on a concept",
}

# Data is embedded locally; only the pinned renderer is fetched from the CDN.
page = (BASE / "graph_view.html").read_text(encoding="utf-8")
page = page.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))
components.html(page, height=825, scrolling=False)
st.caption("Drag to orbit | Scroll to zoom | Right-drag to pan | Select a concept or relationship to explore. The 3D renderer requires an internet connection and WebGL.")
