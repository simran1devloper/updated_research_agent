"""
Reusable UI components for the Streamlit frontend.
Inspired by testing_AI_Agent_Project/ui.py — adapted for microservices app.py.
"""
import re
import json
import streamlit as st
import streamlit.components.v1 as components


_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

    .main-header {
        font-size: 2.5rem; font-weight: 700;
        background: linear-gradient(120deg, #2E86AB 0%, #06BCC1 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle { font-size: 1.1rem; color: #888; margin-bottom: 2rem; }

    .node-badge {
        display: inline-block; padding: 0.2rem 0.65rem; border-radius: 12px;
        font-size: 0.78rem; font-weight: 600; margin: 0.2rem;
        font-family: 'IBM Plex Mono', monospace; letter-spacing: 0.02em;
    }
    .node-guard            { background-color: #E3F2FD; color: #1565C0; }
    .node-context          { background-color: #F3E5F5; color: #6A1B9A; }
    .node-intentorchestrator { background-color: #E8F5E9; color: #2E7D32; }
    .node-planner          { background-color: #FFF3E0; color: #E65100; }
    .node-quickmode        { background-color: #E0F2F1; color: #00695C; }
    .node-deepresearch     { background-color: #FCE4EC; color: #AD1457; }
    .node-gapanalysis      { background-color: #FFF9C4; color: #F57F17; }
    .node-synthesize       { background-color: #EDE7F6; color: #4527A0; }
    .node-formatter        { background-color: #C5CAE9; color: #283593; }
    .node-clarifyuser      { background-color: #FBE9E7; color: #BF360C; }

    .clarification-card {
        background: linear-gradient(135deg, #fff8e1 0%, #fff3e0 100%);
        border-left: 4px solid #FF8F00; border-radius: 8px;
        padding: 1rem 1.25rem; margin: 0.5rem 0;
    }
    .clarification-card .clarification-title {
        font-size: 1rem; font-weight: 700; color: #E65100; margin-bottom: 0.5rem;
    }

    .badge-ok           { color: #34a853; font-weight: 700; }
    .badge-degraded     { color: #fbbc04; font-weight: 700; }
    .badge-unreachable  { color: #ea4335; font-weight: 700; }

    .meta-card {
        background: #1e1e1e; border: 1px solid #333;
        border-radius: 8px; padding: 12px; margin-top: 8px;
    }
</style>
"""


def apply_global_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def render_header() -> None:
    st.markdown('<h1 class="main-header">🔬 AI Research Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Ask complex technical questions and get detailed, research-backed answers</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(threads: dict, active_id: str, on_new_thread, on_select_thread) -> None:
    with st.sidebar:
        st.markdown("### 💬 Research Agent")
        st.divider()

        if st.button("➕ New Thread", use_container_width=True, type="primary"):
            on_new_thread()

        st.subheader("Threads")
        for tid, thread in threads.items():
            label = ("📌 " if tid == active_id else "💬 ") + thread["name"]
            if st.button(label, key=f"thread_{tid}", use_container_width=True):
                on_select_thread(tid)

        st.divider()
        st.caption("Powered by LangGraph + Ollama")


# ---------------------------------------------------------------------------
# Execution path
# ---------------------------------------------------------------------------

def _node_badge(node_name: str) -> str:
    css_key = node_name.lower().replace("_", "").replace(" ", "")
    return f'<span class="node-badge node-{css_key}">{node_name}</span>'


def render_execution_path(nodes: list) -> None:
    if not nodes:
        return
    badges = " → ".join(_node_badge(n) for n in nodes)
    st.markdown(f"**Execution Path:** {badges}", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

def render_chat_history(history: list[dict]) -> None:
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                path = msg.get("execution_path", [])
                if path:
                    render_execution_path(path)

                if msg.get("is_clarification"):
                    render_clarification_request(content)
                else:
                    render_content_with_mermaid(content)


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------

def render_result_metadata(result: dict) -> None:
    if not result:
        return
    with st.expander("Research Metadata", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("Mode", (result.get("mode") or "—").upper())
        col2.metric("Iterations", result.get("iterations", 0))
        col3.metric("Tokens used", result.get("token_usage", 0))

        path = result.get("execution_path", [])
        if path:
            st.markdown("**Execution path:**")
            render_execution_path(path)

        sources = result.get("sources", [])
        if sources:
            st.markdown("**Sources:**")
            for url in sources[:10]:
                if url:
                    st.markdown(f"- {url}")


# ---------------------------------------------------------------------------
# Health panel
# ---------------------------------------------------------------------------

def render_health_panel(health_data: dict) -> None:
    overall = health_data.get("overall", "unknown")
    css_class = {"ok": "badge-ok", "degraded": "badge-degraded"}.get(overall, "badge-unreachable")
    st.markdown(f'<span class="{css_class}">● {overall.upper()}</span>', unsafe_allow_html=True)

    services = health_data.get("services", {})
    for name, status in services.items():
        icon = "✅" if status == "ok" else "❌"
        st.caption(f"{icon} {name}: {status}")


# ---------------------------------------------------------------------------
# Clarification
# ---------------------------------------------------------------------------

def render_clarification_request(message: str) -> None:
    st.markdown(
        "<div class='clarification-card'>"
        "<div class='clarification-title'>🔍 Clarification Needed</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(message)


# ---------------------------------------------------------------------------
# Mermaid rendering
# ---------------------------------------------------------------------------

def _sanitize_mermaid_code(code: str) -> str:
    code = code.strip()
    code = re.sub(r'^```(?:mermaid)?\s*\n?', '', code, flags=re.IGNORECASE)
    code = re.sub(r'\n?```\s*$', '', code)
    code = code.strip()

    def replace_literal_newlines(m):
        inner = m.group(1).replace('\\n', ' ').replace('\\t', ' ')
        return f'["{inner}"]'
    code = re.sub(r'\["([^"]*?)"\]', replace_literal_newlines, code)

    def collapse_real_newlines(m):
        inner = re.sub(r'\s*\n\s*', ' ', m.group(1))
        return f'["{inner}"]'
    code = re.sub(r'\["(.*?)"\]', collapse_real_newlines, code, flags=re.DOTALL)

    code = re.sub(r'(--[->\\.]+)\s*\n\s*(\|[^|]+\|)', r'\1\2', code)
    code = re.sub(r'(-{2,}>)\s*\n\s*\|', r'\1|', code)
    code = re.sub(r'(--[->\\.]+)\s+\|', r'\1|', code)
    code = re.sub(r'(---)\s+\|', r'\1|', code)
    code = re.sub(r'--->', '-->', code)

    lines = code.split('\n')
    code = '\n'.join(
        l for l in lines
        if not re.match(r'^(style|classDef|class|linkStyle)\s+', l.strip(), re.IGNORECASE)
    )

    valid_starts = (
        'graph ', 'graph\n', 'flowchart ', 'flowchart\n',
        'sequencediagram', 'classdiagram', 'statediagram',
        'erdiagram', 'gantt', 'pie', 'journey', 'gitgraph',
        'mindmap', 'timeline',
    )
    if not any(code.split('\n')[0].strip().lower().startswith(v) for v in valid_starts):
        code = 'flowchart TD\n' + code

    return code.strip()


def render_mermaid(mermaid_code: str, height: int = 520) -> None:
    code = _sanitize_mermaid_code(mermaid_code)
    js_code = json.dumps(code)

    html_code = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d1117; font-family: 'Segoe UI', system-ui, sans-serif; overflow: hidden; height: {height}px; }}
  #toolbar {{
    position: absolute; top: 10px; right: 12px; z-index: 100;
    display: flex; align-items: center; gap: 4px;
    background: rgba(22,27,34,0.92); border: 1px solid #30363d;
    border-radius: 10px; padding: 5px 8px; backdrop-filter: blur(6px);
  }}
  .tb-btn {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    color: #8b949e; cursor: pointer; width: 30px; height: 30px;
    display: flex; align-items: center; justify-content: center; font-size: 15px;
  }}
  .tb-btn:hover {{ background: #21262d; border-color: #388bfd; color: #c9d1d9; }}
  #zoom-label {{ font-size: 11px; color: #8b949e; min-width: 36px; text-align: center; }}
  .tb-divider {{ width: 1px; height: 20px; background: #30363d; margin: 0 2px; }}
  #viewport {{ position: absolute; inset: 0; overflow: hidden; cursor: grab; }}
  #viewport.dragging {{ cursor: grabbing; }}
  #canvas {{ position: absolute; top: 0; left: 0; transform-origin: 0 0; will-change: transform; }}
  #canvas svg {{ display: block; max-width: none !important; height: auto; }}
  #error-box {{
    display: none; position: absolute; inset: 10px;
    background: #1a0a0a; border: 1px solid #f44336; border-radius: 8px;
    padding: 14px; color: #f44336; font-family: monospace; font-size: 13px;
    white-space: pre-wrap; overflow: auto; z-index: 200;
  }}
  #hint {{
    position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
    font-size: 11px; color: #484f58; pointer-events: none; white-space: nowrap;
  }}
</style></head><body>
<div id="toolbar">
  <button class="tb-btn" id="btn-zoom-in" title="Zoom in">＋</button>
  <button class="tb-btn" id="btn-zoom-out" title="Zoom out">－</button>
  <span id="zoom-label">100%</span>
  <div class="tb-divider"></div>
  <button class="tb-btn" id="btn-fit" title="Fit to screen">⊡</button>
  <button class="tb-btn" id="btn-reset" title="Reset">↺</button>
</div>
<div id="viewport"><div id="canvas"><div id="mermaid-div"></div></div></div>
<div id="error-box"></div>
<div id="hint">Scroll to zoom · Drag to pan</div>
<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
const diagramCode = {js_code};
mermaid.initialize({{
  startOnLoad: false, theme: 'dark', securityLevel: 'loose', logLevel: 'error',
  themeVariables: {{
    primaryColor: '#1f6feb', primaryTextColor: '#c9d1d9', primaryBorderColor: '#388bfd',
    lineColor: '#8b949e', secondaryColor: '#21262d', tertiaryColor: '#0d1117',
    background: '#0d1117', mainBkg: '#161b22', nodeBorder: '#388bfd',
  }},
  flowchart: {{ useMaxWidth: false, htmlLabels: true, curve: 'basis' }},
}});
let scale = 1, offsetX = 0, offsetY = 0;
const MIN = 0.1, MAX = 5, STEP = 0.15;
const viewport = document.getElementById('viewport');
const canvas = document.getElementById('canvas');
const zoomLabel = document.getElementById('zoom-label');
function applyTransform() {{
  canvas.style.transform = `translate(${{offsetX}}px, ${{offsetY}}px) scale(${{scale}})`;
  zoomLabel.textContent = Math.round(scale * 100) + '%';
}}
function fitToScreen() {{
  const svgEl = canvas.querySelector('svg');
  if (!svgEl) return;
  const vw = viewport.clientWidth, vh = viewport.clientHeight;
  const sw = svgEl.getBoundingClientRect().width / scale;
  const sh = svgEl.getBoundingClientRect().height / scale;
  scale = Math.max(MIN, Math.min(vw / sw, vh / sh, MAX) * 0.92);
  offsetX = (vw - sw * scale) / 2;
  offsetY = Math.max(16, (vh - sh * scale) / 2);
  applyTransform();
}}
function zoomAround(ns, cx, cy) {{
  ns = Math.max(MIN, Math.min(MAX, ns));
  const f = ns / scale;
  offsetX = cx - f * (cx - offsetX);
  offsetY = cy - f * (cy - offsetY);
  scale = ns; applyTransform();
}}
document.getElementById('btn-zoom-in').addEventListener('click', () => zoomAround(scale + STEP, viewport.clientWidth/2, viewport.clientHeight/2));
document.getElementById('btn-zoom-out').addEventListener('click', () => zoomAround(scale - STEP, viewport.clientWidth/2, viewport.clientHeight/2));
document.getElementById('btn-fit').addEventListener('click', fitToScreen);
document.getElementById('btn-reset').addEventListener('click', () => {{ scale=1; offsetX=20; offsetY=20; applyTransform(); }});
viewport.addEventListener('wheel', (e) => {{
  e.preventDefault();
  const r = viewport.getBoundingClientRect();
  zoomAround(scale * (1 - e.deltaY * 0.001), e.clientX - r.left, e.clientY - r.top);
}}, {{ passive: false }});
let isDragging=false, dragStartX=0, dragStartY=0;
viewport.addEventListener('mousedown', (e) => {{ if(e.button!==0) return; isDragging=true; dragStartX=e.clientX-offsetX; dragStartY=e.clientY-offsetY; viewport.classList.add('dragging'); }});
window.addEventListener('mousemove', (e) => {{ if(!isDragging) return; offsetX=e.clientX-dragStartX; offsetY=e.clientY-dragStartY; applyTransform(); }});
window.addEventListener('mouseup', () => {{ isDragging=false; viewport.classList.remove('dragging'); }});
async function renderDiagram() {{
  const container = document.getElementById('mermaid-div');
  const errorBox = document.getElementById('error-box');
  try {{
    const {{ svg }} = await mermaid.render('mermaid-svg', diagramCode);
    container.innerHTML = svg;
    requestAnimationFrame(() => requestAnimationFrame(() => {{
      const svgEl = container.querySelector('svg');
      if (svgEl) {{ svgEl.removeAttribute('width'); svgEl.style.maxWidth = 'none'; }}
      fitToScreen();
    }}));
  }} catch(err) {{
    container.style.display = 'none';
    errorBox.style.display = 'block';
    errorBox.textContent = '⚠️ Diagram render error:\\n' + (err.message || String(err));
  }}
}}
renderDiagram();
</script></body></html>"""
    components.html(html_code, height=height, scrolling=False)


def _extract_mermaid_blocks(content: str):
    parts = []
    pattern = re.compile(r'```mermaid\s*\n(.*?)```', re.DOTALL | re.IGNORECASE)
    last_end = 0
    for match in pattern.finditer(content):
        text_before = content[last_end:match.start()]
        if text_before.strip():
            parts.append(('text', text_before))
        mermaid_code = match.group(1).strip()
        if mermaid_code:
            parts.append(('mermaid', mermaid_code))
        last_end = match.end()
    remaining = content[last_end:]
    if remaining.strip():
        parts.append(('text', remaining))
    return parts


def render_content_with_mermaid(content: str) -> None:
    if not content:
        return
    content = content.strip()

    while True:
        old = content
        content = re.sub(r'^```(?:markdown|text|md)?\s*\n?', '', content, flags=re.IGNORECASE)
        content = re.sub(r'\n?```\s*$', '', content)
        if content == old:
            break
    content = content.strip()

    if '```mermaid' not in content.lower():
        st.markdown(content)
        return

    for part_type, part_content in _extract_mermaid_blocks(content):
        if part_type == 'mermaid':
            render_mermaid(part_content)
        else:
            cleaned = part_content.strip()
            if cleaned:
                st.markdown(cleaned)
