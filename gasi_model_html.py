"""Local, repeatable HTML view of the Markdown data model; no openBIS access."""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
import re
import sys
import textwrap

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "docs" / "GaSi_Datenmodell.md"

STYLE = """
:root { color-scheme: light; --ink:#183448; --muted:#526b7b; --blue:#126b88;
  --line:#d9e4e9; --paper:#fff; --wash:#f0f5f7; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; scroll-padding-top:90px; }
body { margin:0; background:var(--wash); color:var(--ink);
  font:16px/1.7 system-ui,-apple-system,"Segoe UI",sans-serif; }
a { color:var(--blue); text-underline-offset:3px; overflow-wrap:anywhere; }
a:hover { color:#084a60; }
a:focus-visible,button:focus-visible,input:focus-visible { outline:3px solid #d78627; outline-offset:3px; }
.toolbar { position:sticky; top:0; z-index:2; display:flex; align-items:center;
  flex-wrap:wrap; gap:16px; padding:13px 28px; background:#12384b; color:white; }
.brand { font-weight:750; letter-spacing:.05em; margin-right:auto; }
.toolbar input { width:min(300px,55vw); border:1px solid #638497; padding:9px 12px;
  border-radius:6px; font:inherit; background:#fff; color:var(--ink); }
button { border:1px solid #9cb5c3; border-radius:6px; padding:9px 14px;
  font:inherit; cursor:pointer; background:#fff; color:var(--ink); }
.layout { display:grid; grid-template-columns:260px minmax(0,1fr); max-width:1600px; margin:auto; }
aside { padding:28px 22px; position:sticky; top:76px; align-self:start; max-height:calc(100vh - 82px); overflow:auto; }
.nav-title { font-size:.78rem; font-weight:750; letter-spacing:.12em; text-transform:uppercase; }
.toc ul { list-style:none; margin:10px 0; padding:0; }
.toc li { margin:9px 0; line-height:1.4; }
.toc li ul { padding-left:13px; border-left:2px solid var(--line); }
.toc a { color:var(--muted); text-decoration:none; font-size:.88rem; }
.toc a:hover { color:var(--blue); text-decoration:underline; }
main { min-width:0; margin:24px 24px 40px 0; background:var(--paper);
  border:1px solid var(--line); border-radius:12px; box-shadow:0 8px 26px #18344808; }
.intro { padding:28px 38px 22px; border-bottom:1px solid var(--line); background:#f8fbfc; border-radius:12px 12px 0 0; }
.eyebrow { color:var(--blue); font-size:.78rem; font-weight:750; text-transform:uppercase; letter-spacing:.1em; }
.intro p { margin:8px 0 0; color:var(--muted); max-width:78ch; }
.legend { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }
.legend span { border:1px solid var(--line); padding:4px 10px; border-radius:20px; font-size:.82rem; background:white; }
article { padding:8px 38px 36px; }
h1,h2,h3 { line-height:1.25; color:#12384b; }
h1 { font-size:clamp(1.8rem,3vw,2.65rem); letter-spacing:-.025em; margin:28px 0; }
h2 { margin:48px 0 20px; padding-top:24px; border-top:1px solid var(--line); font-size:1.5rem; }
h3 { margin-top:30px; font-size:1.12rem; }
.headerlink { margin-left:.25em; font-size:.65em; text-decoration:none; opacity:0; }
h1:hover .headerlink,h2:hover .headerlink,h3:hover .headerlink,.headerlink:focus { opacity:1; }
p,li { max-width:95ch; }
li { margin:7px 0; }
code { font: .88em/1.5 ui-monospace,Consolas,monospace; padding:2px 5px;
  background:#edf3f6; border-radius:4px; overflow-wrap:anywhere; }
pre { overflow:auto; padding:18px; background:#123448; color:#edf8fc; border-radius:8px; }
pre code { background:transparent; color:inherit; padding:0; white-space:pre; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:8px; margin:22px 0; }
table { border-collapse:collapse; width:100%; font-size:.88rem; min-width:720px; }
th,td { padding:13px 15px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { background:#e9f2f6; font-weight:700; }
tr:last-child td { border-bottom:0; }
tbody tr:nth-child(even) { background:#f7fafb; }
td:first-child { font-weight:600; min-width:130px; }
blockquote { border-left:4px solid #3c8fa4; margin:20px 0; padding:5px 20px; background:#f1f8fa; }
figure { margin:22px 0; padding:16px; border:1px solid var(--line); border-radius:8px; }
.diagram { overflow:auto; }
.diagram svg { display:block; max-width:none; height:auto; }
figcaption,summary { color:var(--muted); font-size:.85rem; }
summary { cursor:pointer; margin-top:10px; }
.diagram-warning { padding:12px; background:#fff4df; }
footer { border-top:1px solid var(--line); padding:20px 38px; color:var(--muted); font-size:.83rem; overflow-wrap:anywhere; }
mark { background:#ffe18a; color:#183448; }
#search-count { font-size:.8rem; }
.skip { position:absolute; left:-9999px; }
.skip:focus { left:10px; top:10px; z-index:5; padding:10px; background:white; }
@media(max-width:950px) { .layout { display:block; } aside { position:static; max-height:240px; padding:18px 22px; }
  main { margin:0 12px 24px; } article,.intro { padding-left:20px; padding-right:20px; }
  .toolbar { padding:12px 18px; } }
@media print { body { background:white; font-size:10pt; } .toolbar,aside,.intro,details,.skip { display:none; }
  .layout { display:block; } main { border:0; box-shadow:none; margin:0; } article { padding:0; }
  h2,h3 { break-after:avoid; } tr,figure { break-inside:avoid; } .table-wrap,.diagram { overflow:visible; }
  table { min-width:0; font-size:8pt; } th,td { padding:6px; } .diagram svg { width:100%; }
  a { color:inherit; } }
"""

# Compact first: the source document remains available in closed accordions.
STYLE += """
html { scroll-behavior:auto; }
.toolbar { padding:10px max(22px,calc((100vw - 1320px)/2)); gap:14px; }
.toolbar input { width:230px; padding:6px 10px; font-size:.88rem; }
.toolbar button { padding:6px 11px; font-size:.88rem; }
.toolbar nav { display:flex; gap:18px; margin-right:12px; }
.toolbar nav a { color:#d3e9f1; text-decoration:none; font-size:.88rem; }
.layout { display:block; max-width:1360px; padding:0 24px; }
main { margin:0 0 32px; background:transparent; border:0; box-shadow:none; }
.hero { display:flex; align-items:center; justify-content:space-between; gap:24px; padding:25px 0 20px; }
.hero h1 { margin:0 0 6px; font-size:clamp(1.65rem,3vw,2.25rem); }
.hero p { margin:0; color:var(--muted); font-size:.94rem; }
.status-pill { flex-shrink:0; color:#825416; background:#fff4dc; border:1px solid #ecd5a8;
  border-radius:18px; padding:5px 12px; font-size:.8rem; }
article { padding:0; }
figure { margin:0; padding:18px 22px 14px; background:white; border-radius:12px; }
.figure-heading { display:flex; gap:12px; align-items:center; justify-content:space-between; }
.figure-heading h2 { margin:0; padding:0; border:0; font-size:1.1rem; }
.graph-controls { display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.graph-controls button { padding:5px 10px; font-size:.82rem; }
.diagram { overflow:auto; margin-top:12px; cursor:default; max-height:calc(100vh - 205px); }
.diagram svg { display:block; width:100%; max-width:none; height:auto; max-height:calc(100vh - 220px); }
figcaption { display:flex; flex-wrap:wrap; gap:18px; margin-top:8px; font-size:.78rem; }
.line-key::before { content:''; display:inline-block; width:24px; border-top:2px solid #47768d;
  vertical-align:middle; margin-right:6px; }
.line-key.dataset::before { border-top:2px dashed #ad771e; }
.line-key.property::before { border-top:2px dotted #7b8691; }
figure:fullscreen { background:#fff; border:0; border-radius:0; display:flex; flex-direction:column;
  width:100vw; height:100vh; padding:20px; }
figure:fullscreen .diagram { flex:1; min-height:0; max-height:none; }
figure:fullscreen .diagram svg { width:100%; height:100%; max-height:none; object-fit:contain; }
.levels { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin:18px 0 26px; }
.level-card { padding:16px 18px; background:#fff; border:1px solid var(--line); border-radius:10px; }
.level-card h3 { margin:0 0 7px; font-size:1rem; }
.level-card p { margin:0; font-size:.87rem; line-height:1.55; color:var(--muted); }
.details-heading { margin:0 0 12px; padding:0; border:0; font-size:1.15rem; }
details.model-section { border:1px solid var(--line); border-radius:8px; background:white; margin:8px 0; }
details.model-section > summary { padding:13px 18px; margin:0; color:var(--ink); font-size:.93rem; font-weight:650; }
details.model-section[open] > summary { border-bottom:1px solid var(--line); }
.section-body { padding:0 22px 20px; }
.section-body > h2:first-child { position:absolute; width:1px; height:1px; overflow:hidden; padding:0; margin:0; border:0; }
.section-body p,.section-body li { font-size:.92rem; }
.toc { padding:15px 0; }
.toc ul { columns:2; }
.toc li { break-inside:avoid; }
.toc a { color:var(--blue); }
.source-note { padding:16px 0; border:0; font-size:.8rem; }
.source-note details { margin-top:8px; }
.source-note summary { margin:0; }
.expert-view { margin-top:18px; background:#fff; border:1px solid var(--line); border-radius:10px; }
.expert-view > summary { margin:0; padding:14px 18px; font-size:.9rem; font-weight:600; }
.expert-content { padding:0 18px 18px; }
.detail-search { display:flex; flex-wrap:wrap; align-items:center; gap:10px; margin:18px 0; }
.detail-search input { padding:8px 12px; border:1px solid var(--line); border-radius:5px; font:inherit; }
.technical-diagrams { margin:16px 0; }
.simple-note { display:block; font-size:.9rem; }
.hero h1 { font-size:clamp(1.5rem,2.6vw,2.05rem); }
.diagram-source summary { font-size:.85rem; }
@media(max-width:850px) { .toolbar { padding:10px 16px; } .toolbar nav { display:none; }
  .layout { padding:0 14px; } .hero { align-items:flex-start; flex-direction:column; gap:10px; }
  figure { padding:14px; } .figure-heading { align-items:flex-start; flex-direction:column; }
  .levels { grid-template-columns:1fr; } .level-card { padding:13px 16px; }
  .toc ul { columns:1; } .section-body { padding:0 16px 16px; } }
@media print { .hero { padding:0 0 15px; } .graph-controls,.source-note { display:none; }
  .layout { padding:0; } figure { padding:10px; } .diagram { overflow:visible; }
  .diagram { max-height:none; } .diagram svg { width:100% !important; max-height:none !important; } .level-card { padding:10px; }
  .levels { gap:10px; } .level-card p { font-size:8pt; } }
"""

SCRIPT = """
const article = document.querySelector('article');
const query = document.getElementById('search');
const counter = document.getElementById('search-count');
let timer;
query?.addEventListener('input', () => {
  clearTimeout(timer);
  timer = setTimeout(() => {
    article.querySelectorAll('mark').forEach(mark => mark.replaceWith(document.createTextNode(mark.textContent)));
    article.normalize();
    const term = query.value.trim();
    counter.textContent = '';
    if (!term) return;
    const walker = document.createTreeWalker(article, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.parentElement.closest('svg,script,style') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    let count = 0;
    for (const node of nodes) {
      const value = node.nodeValue;
      const lower = value.toLocaleLowerCase('de');
      const needle = term.toLocaleLowerCase('de');
      let offset = 0, at = lower.indexOf(needle);
      if (at < 0) continue;
      const fragment = document.createDocumentFragment();
      while (at >= 0) {
        fragment.append(document.createTextNode(value.slice(offset, at)));
        const mark = document.createElement('mark');
        mark.textContent = value.slice(at, at + term.length);
        fragment.append(mark);
        count++;
        offset = at + term.length;
        at = lower.indexOf(needle, offset);
      }
      fragment.append(document.createTextNode(value.slice(offset)));
      node.replaceWith(fragment);
    }
    counter.textContent = count + ' Treffer';
    const first = article.querySelector('mark');
    if (first) { openParents(first); first.scrollIntoView({block:'center'}); }
  }, 180);
});
document.getElementById('print').addEventListener('click', () => window.print());
function openParents(element) {
  let parent = element.parentElement;
  while (parent) { if (parent.tagName === 'DETAILS') parent.open = true; parent = parent.parentElement; }
}
document.querySelectorAll('a[href^="#"]').forEach(link => link.addEventListener('click', event => {
  const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
  if (target) { event.preventDefault(); openParents(target); target.scrollIntoView({block:'start'}); }
}));
document.querySelectorAll('figure[data-graph]').forEach(figure => {
  const svg = figure.querySelector('svg');
  const viewport = figure.querySelector('.diagram');
  let scale = 1;
  figure.querySelectorAll('[data-zoom]').forEach(button => button.addEventListener('click', () => {
    scale = button.dataset.zoom === 'fit' ? 1 : Math.max(.5, Math.min(3, scale + (button.dataset.zoom === 'in' ? .25 : -.25)));
    svg.style.width = (scale * 100) + '%';
    svg.style.height = 'auto';
    svg.style.maxHeight = scale === 1 ? '' : 'none';
    viewport.style.cursor = scale > 1 ? 'grab' : 'default';
    if (scale === 1) { viewport.scrollLeft = 0; viewport.scrollTop = 0; }
  }));
  figure.querySelector('[data-fullscreen]').addEventListener('click', async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await figure.requestFullscreen();
    } catch (_) { figure.querySelector('[data-fullscreen]').textContent = 'Bitte Browser maximieren'; }
  });
  document.addEventListener('fullscreenchange', () => {
    scale = 1; svg.style.width = '100%'; svg.style.height = ''; svg.style.maxHeight = '';
    figure.querySelector('[data-fullscreen]').textContent = document.fullscreenElement === figure ? 'Zurück' : 'Größer ansehen';
    viewport.scrollLeft = 0; viewport.scrollTop = 0;
  });
  let drag = null;
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0 || scale <= 1) return;
    drag = {x:event.clientX, y:event.clientY, left:viewport.scrollLeft, top:viewport.scrollTop};
    viewport.setPointerCapture(event.pointerId);
    viewport.style.cursor = 'grabbing';
    event.preventDefault();
  });
  viewport.addEventListener('pointermove', event => {
    if (!drag) return;
    viewport.scrollLeft = drag.left - event.clientX + drag.x;
    viewport.scrollTop = drag.top - event.clientY + drag.y;
  });
  const stopDrag = () => { drag = null; viewport.style.cursor = scale > 1 ? 'grab' : 'default'; };
  viewport.addEventListener('pointerup', stopDrag);
  viewport.addEventListener('pointercancel', stopDrag);
});
"""

def _node_caption(label):
    prefix, _, description = label.partition(" / ")
    area, colon, type_code = prefix.partition(": ")
    if colon:
        if re.fullmatch(r"[A-Z_]+", description):
            return f"{type_code} / {description}", area
        return description[:1].upper() + description[1:] if description else type_code, f"{type_code} · {area}"
    return (description[:1].upper() + description[1:], prefix) if description else (label, "")


def _plain_caption(label):
    """Display vocabulary only; technical labels and relationships stay in the source."""
    if "EXPERIMENTAL_STEP" in label:
        return "Messung", "Ein zusammengehöriger Messlauf."
    if "SETUP.TEST" in label:
        return "Aktueller Aufbau", "Die bestätigte Zuordnung von Geräten, Positionen und Kanälen."
    if " / GaSi-Anlage" in label:
        return "GaSi-Anlage", "Die gesamte Einrichtung."
    if " / Module" in label:
        return "Module", "Gasmischung, Befeuchter und Messkette."
    if " / Geräte" in label:
        return "Geräte", "Einzeln identifizierbare Geräte des aktuellen Aufbaus."
    if "GAS_BOTTLE" in label:
        return "Prüfgas", "Das zertifizierte Gas für die Messung." if "zertifiziert" in label else "Das Gas für die Messung."
    if "DUT" in label:
        return "Prüfling", "Das Gerät oder der Sensor, der geprüft wird." + (" Die genaue Zuordnung bleibt zu klären." if "falls identifiziert" in label else "")
    if "MBW-Referenz" in label:
        return "Vergleichsgerät", "Das Referenzgerät liefert Werte zum Vergleichen."
    if "SOP" in label or "SOFTWARE_CODE" in label:
        return "Anleitung & Programm", "Das verwendete Verfahren und die verwendete Software."
    if "RAW_DATA" in label:
        return "Messwerte", "Die unveränderte Messdatei."
    if "Konfigurationssnapshot" in label:
        return "Einstellungen", "Die für diesen Lauf gespeicherten Einstellungen."
    if "Messprotokoll" in label:
        return "Messprotokoll", "Das während der Aufnahme erzeugte Protokoll."
    if "Auswertung" in label:
        return "Auswertung", "Ergebnisse und Bericht zur Messung."
    if "CALIBRATION" in label:
        return "Kalibrierung", "Der Kalibriernachweis zum Gerät."
    return _node_caption(label)[0], ""


def _current_setup_svg(labels, activity, parents, datasets, extra, *, simple):
    """Inventar oben, Verwendung unten; getrennte Linien ohne Boxüberschneidung."""
    setup = next(key for key, label in labels.items() if "SETUP.TEST" in label)
    physical = [e for e in extra if not e[2].casefold().startswith("object property")]
    calibration = [e for e in extra if e not in physical]
    if len(physical) != 3 or len(calibration) > 1:
        raise ValueError("Aufbau-Grafik benötigt genau die Kette Anlage, Modul, Gerät, Aufbau.")
    device = next(e[0] for e in physical if e[1] == setup)
    module = next(e[0] for e in physical if e[1] == device)
    plant = next(e[0] for e in physical if e[1] == module)
    if {e[:2] for e in physical} != {(plant, module), (module, device), (device, setup)}:
        raise ValueError("Aufbau-Zuordnung ist nicht eindeutig.")
    if len(parents) > 4 or len(datasets) > 3 or {e[0] for e in parents} & {plant, module}:
        raise ValueError("Erweiterter Aufbau: Diagrammquelle verwenden.")
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 650" role="img" '
             'aria-label="GaSi-Anlage, Module und Geräte bilden den aktuellen Aufbau. Dieser wird bei einer Messung verwendet.">',
             '<defs><marker id="setup-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#527b8f"/></marker></defs>']
    def node(key, x, y, width, height, reference=False):
        title, help_text = _plain_caption(labels[key]) if simple else _node_caption(labels[key])
        lines = textwrap.wrap(title, width=27 if simple else 31)
        attr = 'data-reference' if reference else 'data-node'
        fill, color = ("#12384b", "white") if key == activity else ("white", "#183448")
        parts.append(f'<g {attr}="{escape(key)}"><title>{escape(help_text or labels[key])}</title>'
                     f'<rect class="node-box" x="{x}" y="{y}" width="{width}" height="{height}" rx="9" fill="{fill}" stroke="#b9ced9"/>')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x+width/2}" y="{y+height/2+6+(i-(len(lines)-1)/2)*20}" text-anchor="middle" font-family="sans-serif" font-size="17" font-weight="600" fill="{color}">{escape(line)}</text>')
        parts.append('</g>')
    def line(start, end, path, caption, x, y):
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(caption)}</title>'
                     f'<path class="connection" d="{path}" fill="none" stroke="#527b8f" stroke-width="2" marker-end="url(#setup-arrow)"/>'
                     f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#526b7b">{escape(caption)}</text></g>')
    for key, x, w in ((plant, 24, 292), (module, 460, 280), (device, 908, 268)):
        node(key, x, 28, w, 68)
    line(plant, module, 'M316,62 H460', 'umfasst', 388, 49)
    line(module, device, 'M740,62 H908', 'umfasst', 824, 49)
    line(device, setup, 'M1042,96 V146 H170 V202', 'Position / Kanal', 600, 133)
    parts.append('<rect x="24" y="186" width="292" height="304" rx="12" fill="#eaf3f8"/>'
                 '<rect x="908" y="186" width="268" height="304" rx="12" fill="#fff4df"/>')
    for i, (start, end, relation) in enumerate(parents):
        node(start, 36, 202+i*70, 268, 60, reference=start == device)
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(relation)}</title></g>')
    node(activity, 460, 287, 280, 100)
    for i, (start, end, relation) in enumerate(datasets):
        node(end, 920, 215+i*92, 244, 68)
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(relation)}</title></g>')
    for x1, x2, caption in ((316, 460, 'für'), (740, 908, 'speichert')):
        parts.append(f'<path class="connection" d="M{x1},337 H{x2}" fill="none" stroke="#527b8f" stroke-width="2" marker-end="url(#setup-arrow)"/>'
                     f'<text x="{(x1+x2)/2}" y="324" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#526b7b">{caption}</text>')
    for start, end, relation in calibration:
        node(start, 24, 553, 292, 60)
        node(end, 460, 553, 280, 60, reference=True)
        line(start, end, 'M316,583 H460', 'Nachweis für', 388, 570)
    return ''.join(parts) + '</svg>'


def _plain_measurement_svg(labels, activity, parents, datasets, extra):
    """Grouped inputs/outputs need only two straight arrows and no crossing buses."""
    top, row, padding = 64, 66, 16
    rows = max(len(parents), len(datasets), 1)
    group_height = rows * row + padding * 2
    middle = top + group_height / 2
    extra_top = top + group_height + 42
    height = extra_top + len(extra) * 78 + 12 if extra else top + group_height + 20
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" '
        'role="img" aria-label="Prüfgas, Geräte, Prüfling und Anleitung werden für eine Messung benutzt. Messwerte, Einstellungen und Auswertung gehören zu dieser Messung.">',
        '<defs><marker id="plain-arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 Z" fill="#527b8f"/></marker></defs>']
    for x, title in ((24, "Was wird benutzt?"), (460, "Die Messung"), (908, "Was wird gespeichert?")):
        parts.append(f'<text x="{x}" y="32" font-family="sans-serif" font-size="18" font-weight="650" fill="#183448">{title}</text>')
    parts.append(f'<rect x="24" y="{top}" width="292" height="{group_height}" rx="14" fill="#eaf3f8"/>'
                 f'<rect x="908" y="{top}" width="268" height="{group_height}" rx="14" fill="#fff4df"/>')

    def icon(x, y, title, color):
        shapes = {
            "Prüfgas": '<rect x="9" y="8" width="16" height="27" rx="5"/><path d="M14 8 V3 H20 V8 M13 16 H21"/>',
            "Vergleichsgerät": '<rect x="3" y="5" width="30" height="28" rx="4"/><path d="M8 24 L15 17 L21 23 L28 12 M10 38 H26"/>',
            "Prüfling": '<rect x="8" y="8" width="21" height="21" rx="4"/><path d="M13 3 V8 M23 3 V8 M13 29 V35 M23 29 V35"/>',
            "Anleitung & Programm": '<path d="M4 5 H18 V33 H4 Z M18 5 H32 V33 H18 M8 12 H14 M22 12 H28 M8 18 H14 M22 18 H28"/>',
            "Messwerte": '<path d="M7 2 H24 L31 9 V35 H7 Z M24 2 V10 H31 M11 26 L16 20 L21 24 L27 16"/>',
            "Einstellungen": '<path d="M8 5 V33 M18 5 V33 M28 5 V33 M4 13 H12 M14 25 H22 M24 17 H32"/>',
            "Auswertung": '<path d="M5 3 V33 H33 M11 27 V20 H16 V27 M21 27 V11 H26 V27"/>',
            "Messung": '<path d="M4 30 H33 M9 24 L15 13 L23 19 L30 6"/><circle cx="15" cy="13" r="2"/><circle cx="23" cy="19" r="2"/>',
            "Kalibrierung": '<path d="M7 2 H25 L31 9 V35 H7 Z M12 23 L17 28 L26 16"/>',
        }
        drawing = shapes.get(title, '<rect x="5" y="5" width="27" height="27" rx="5"/>')
        return f'<g transform="translate({x},{y})" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{drawing}</g>'

    def node(key, x, y, width, box_height, kind, reference=False):
        title, help_text = _plain_caption(labels[key])
        fill, color = ("#12384b", "white") if kind == "activity" else ("white", "#183448")
        attr = f'data-reference="{escape(key)}"' if reference else f'data-node="{escape(key)}"'
        parts.append(f'<g {attr}><title>{escape(help_text or title)}</title>'
            f'<rect class="node-box" x="{x}" y="{y}" width="{width}" height="{box_height}" rx="9" fill="{fill}" stroke="#cadbe5"/>'
            + icon(x+12, y+(box_height-38)/2, title, color))
        lines = textwrap.wrap(title, width=23)
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x+57}" y="{y+box_height/2+6+(i-(len(lines)-1)/2)*21}" font-family="sans-serif" font-size="18" font-weight="600" fill="{color}">{escape(line)}</text>')
        parts.append('</g>')

    for i, (start, end, _) in enumerate(parents):
        y = top + (group_height - len(parents)*row)/2 + i*row + 5
        node(start, 36, y, 268, row-10, "resource")
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(_plain_caption(labels[start])[0])} wird für die Messung benutzt.</title></g>')
    node(activity, 460, middle-55, 280, 110, "activity")
    for i, (start, end, _) in enumerate(datasets):
        y = top + (group_height - len(datasets)*row)/2 + i*row + 5
        node(end, 920, y, 244, row-10, "dataset")
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(_plain_caption(labels[end])[0])} gehört zur Messung.</title></g>')
    for x1, x2, caption in ((316, 460, "für"), (740, 908, "liefert")):
        parts.append(f'<path class="connection" d="M{x1},{middle} H{x2}" fill="none" stroke="#527b8f" stroke-width="2.2" marker-end="url(#plain-arrow)"/>'
            f'<text x="{(x1+x2)/2}" y="{middle-12}" text-anchor="middle" font-family="sans-serif" font-size="15" fill="#526b7b">{caption}</text>')
    if extra:
        parts.append(f'<text x="24" y="{extra_top-13}" font-family="sans-serif" font-size="15" fill="#526b7b">Nachweis zum Gerät</text>')
    for i, (start, end, _) in enumerate(extra):
        y = extra_top + i*78
        node(start, 24, y, 292, 58, "resource")
        node(end, 460, y, 280, 58, "resource", reference=end in {p[0] for p in parents} or end == activity)
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}">'
            f'<path class="connection" d="M316,{y+29} H460" fill="none" stroke="#527b8f" stroke-width="1.7" marker-end="url(#plain-arrow)"/>'
            f'<text x="388" y="{y+17}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#526b7b">gehört zu</text></g>')
    return "".join(parts) + "</svg>"


def _measurement_svg(labels, activity, parents, datasets, extra):
    """Three columns with separate buses for object links and file attachments."""
    top, step = 56, 74
    main_height = max(len(parents), len(datasets), 1) * step
    middle = top + main_height / 2
    height = top + main_height + 20 + len(extra) * 64
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" '
             'role="img" aria-label="Ressourcen als Parents des Messlaufs; Datasets als Dateianhänge am Messlauf">',
        '<defs><marker id="parent-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#47768d"/></marker>'
        '<marker id="dataset-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#ad771e"/></marker></defs>']
    for x, title, subtitle in ((24, "RESSOURCEN", "Inventar · verwendete Parents"),
                                (460, "MESSLAUF", "Lab Notebook · Aktivität"),
                                (908, "DATEIEN", "Datasets am Messlauf")):
        parts.append(f'<text x="{x}" y="16" font-family="sans-serif" font-size="12" font-weight="700" letter-spacing="1.2" fill="#526b7b">{title}</text>'
                     f'<text x="{x}" y="36" font-family="sans-serif" font-size="12" fill="#526b7b">{subtitle}</text>')

    def paint_node(key, x, y, width, box_height, kind):
        title, subtitle = _node_caption(labels[key])
        fill = {"resource": "#f0f7fa", "activity": "#12384b", "dataset": "#fff8ea"}[kind]
        color = "white" if kind == "activity" else "#183448"
        muted = "#c8e1ec" if kind == "activity" else "#526b7b"
        parts.append(f'<g data-node="{escape(key)}"><title>{escape(labels[key])}</title>'
                     f'<rect x="{x}" y="{y}" width="{width}" height="{box_height}" rx="9" fill="{fill}" stroke="#c7d9e2"/>')
        for i, line in enumerate(textwrap.wrap(title, width=32)):
            parts.append(f'<text x="{x+16}" y="{y+25+i*17}" font-family="sans-serif" font-size="{18 if kind == "activity" else 14}" font-weight="650" fill="{color}">{escape(line)}</text>')
        parts.append(f'<text x="{x+16}" y="{y+box_height-13}" font-family="sans-serif" font-size="11" fill="{muted}">{escape(subtitle)}</text></g>')

    positions = {}
    for i, (start, end, relation) in enumerate(parents):
        y = top + i * step
        positions[start] = (24, y)
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(relation)}</title>'
                     f'<path d="M304,{y+33} H374" fill="none" stroke="#47768d" stroke-width="2"/></g>')
    first_y, last_y = top+33, top+(len(parents)-1)*step+33
    parts.append(f'<path d="M374,{first_y} V{last_y} M374,{middle} H460" fill="none" stroke="#47768d" stroke-width="2" marker-end="url(#parent-arrow)"/>')
    centers = []
    for i, (start, end, relation) in enumerate(datasets):
        center = top + (i+.5) * main_height / len(datasets)
        centers.append(center)
        positions[end] = (908, center-39)
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(relation)}</title>'
                     f'<path d="M842,{center} H908" fill="none" stroke="#ad771e" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#dataset-arrow)"/></g>')
    parts.append(f'<path d="M740,{middle} H842 M842,{min(centers)} V{max(centers)}" fill="none" stroke="#ad771e" stroke-width="2" stroke-dasharray="6 4"/>')
    for start, _, _ in parents:
        paint_node(start, *positions[start], 280, 66, "resource")
    paint_node(activity, 460, middle-47, 280, 94, "activity")
    for _, end, _ in datasets:
        paint_node(end, *positions[end], 268, 78, "dataset")
    for i, (start, end, relation) in enumerate(extra):
        y = top + main_height + 12 + i * 64
        start_title, _ = _node_caption(labels[start])
        end_title, _ = _node_caption(labels[end])
        parts.append(f'<g data-source="{escape(start)}" data-target="{escape(end)}"><title>{escape(labels[start] + " → " + labels[end])}</title>'
            f'<rect x="24" y="{y}" width="1152" height="50" rx="8" fill="#f6f8fa"/>'
            f'<text x="40" y="{y+30}" font-family="sans-serif" font-size="11" fill="#526b7b">WEITERE VERKNÜPFUNG</text>'
            f'<text data-node="{escape(start)}" x="212" y="{y+30}" font-family="sans-serif" font-size="13" fill="#183448">{escape(start_title)}</text>'
            f'<path d="M430,{y+30} H790" fill="none" stroke="#7b8691" stroke-width="1.5" stroke-dasharray="2 3" marker-end="url(#parent-arrow)"/>'
            f'<text x="610" y="{y+19}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#526b7b">{escape(relation)}</text>'
            f'<text x="812" y="{y+30}" font-family="sans-serif" font-size="13" fill="#183448">{escape(end_title)}</text></g>')
    return "".join(parts) + "</svg>"


def _test_plan_svg(labels, edges):
    """Exact test relationships: containment above, parent and attachment in a row."""
    expected = {("IC", "TI"), ("LC", "TR"), ("LC", "TD"), ("TI", "TR"), ("TR", "TD"), ("TD", "TF")}
    if {(a, b) for a, b, _ in edges} != expected:
        raise ValueError("Geänderter Testplan: Diagrammquelle prüfen.")
    positions = {"IC": (24, 20, 300, 68), "LC": (450, 20, 300, 68),
                 "TI": (24, 180, 300, 90), "TR": (450, 180, 300, 90),
                 "TD": (880, 180, 296, 90), "TF": (880, 365, 296, 68)}
    paths = {("IC", "TI"): ("M174,88 V180", 253, 137),
             ("LC", "TR"): ("M600,88 V180", 679, 137),
             ("LC", "TD"): ("M750,54 H1028 V180", 889, 40),
             ("TI", "TR"): ("M324,225 H450", 387, 210),
             ("TR", "TD"): ("M750,225 H880", 815, 210),
             ("TD", "TF"): ("M1028,270 V365", 1110, 322)}
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 455" role="img" aria-label="Geplante openBIS-Beziehungen des synthetischen Schreibtests">',
             '<defs><marker id="test-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#527b8f"/></marker></defs>']
    for start, end, relation in edges:
        path, x, y = paths[start, end]
        caption = {"Parent": "Parent → Child", "Dataset attachment": "Dataset am Lauf"}.get(relation, relation)
        parts.append(f'<g data-source="{start}" data-target="{end}"><title>{escape(relation)}</title>'
            f'<path class="connection" d="{path}" fill="none" stroke="#527b8f" stroke-width="2" marker-end="url(#test-arrow)"/>'
            f'<text x="{x}" y="{y}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="#526b7b">{escape(caption)}</text></g>')
    for key, (x, y, width, height) in positions.items():
        heading, _, detail = labels[key].partition(" / ")
        lines = textwrap.wrap(heading, width=31) + [detail]
        fill, ink = ("#12384b", "white") if key == "TR" else ("white", "#183448")
        parts.append(f'<g data-node="{key}"><title>{escape(labels[key])}</title><rect class="node-box" x="{x}" y="{y}" width="{width}" height="{height}" rx="9" fill="{fill}" stroke="#b9ced9"/>')
        for i, line in enumerate(lines):
            parts.append(f'<text x="{x+width/2}" y="{y+height/2+5+(i-(len(lines)-1)/2)*20}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="{ink}">{escape(line)}</text>')
        parts.append('</g>')
    return ''.join(parts) + '</svg>'


def flowchart_svg(source: str, *, simple: bool = True) -> str:
    """Render the model's simple LR DAG directly from its Mermaid source, offline.

    Unsupported Mermaid syntax is left visible by the caller, never silently
    omitted or replaced with a separately maintained diagram.
    """
    node = r"([A-Za-z][\w]*)(?:\[([^\]]+)\])?"
    edge = re.compile(rf"\s*{node}\s*-->\s*(?:\|([^|]+)\|\s*)?{node}\s*;?\s*")
    labels, edges = {}, []
    lines = [line.strip() for line in source.splitlines() if line.strip() and not line.strip().startswith("%%")]
    if not lines or lines[0] != "flowchart LR":
        raise ValueError("Für die Offline-Grafik wird flowchart LR benötigt.")
    for line in lines[1:]:
        match = edge.fullmatch(line)
        if not match:
            raise ValueError("Erweiterte Mermaid-Syntax: Diagrammquelle wird unverändert angezeigt.")
        start, start_label, relation, end, end_label = match.groups()
        for key, label in ((start, start_label), (end, end_label)):
            labels[key] = label or labels.get(key, key)
        edges.append((start, end, relation or ""))
    if not labels:
        raise ValueError("Das Diagramm enthält keine Beziehungen.")
    if set(labels) == {"IC", "LC", "TI", "TR", "TD", "TF"}:
        return _test_plan_svg(labels, edges)
    rank = {key: 0 for key in labels}
    for _ in labels:
        changed = False
        for start, end, _ in edges:
            if rank[end] <= rank[start]:
                rank[end] = rank[start] + 1
                changed = True
        if not changed:
            break
    else:
        raise ValueError("Zyklisches Diagramm: Quelle statt einer irreführenden Grafik anzeigen.")
    activities = [key for key, label in labels.items() if "EXPERIMENTAL_STEP" in label]
    if len(activities) == 1:
        activity = activities[0]
        parents = [e for e in edges if e[1] == activity and e[2].casefold() == "parent"]
        datasets = [e for e in edges if e[0] == activity and e[2].casefold() == "dataset attachment"]
        extra = [e for e in edges if e not in parents and e not in datasets]
        if parents and datasets and any("SETUP.TEST" in label for label in labels.values()):
            try:
                return _current_setup_svg(labels, activity, parents, datasets, extra, simple=simple)
            except (StopIteration, ValueError) as exc:
                raise ValueError("Aufbau-Grafik nicht unterstützt; Diagrammquelle bleibt sichtbar.") from exc
        if parents and datasets and all(e[2].casefold().startswith("object property") for e in extra):
            render = _plain_measurement_svg if simple else _measurement_svg
            return render(labels, activity, parents, datasets, extra)
    layers = defaultdict(list)
    for key in labels:
        layers[rank[key]].append(key)
    height = max(map(len, layers.values())) * 130 + 50
    width = (max(rank.values()) + 1) * 350
    positions = {key: (25 + level * 350, 25 + (height - 50) * (index + .5) / len(keys) - 44)
                 for level, keys in layers.items() for index, key in enumerate(keys)}
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Gerichtete Beziehungen des GaSi-Datenmodells">',
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="#527b8f"/></marker></defs>']
    for start, end, relation in edges:
        x1, y1 = positions[start]
        x2, y2 = positions[end]
        x1, y1, y2 = x1 + 250, y1 + 44, y2 + 44
        mid = (x1 + x2) / 2
        pieces.append(f'<path d="M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}" fill="none" stroke="#527b8f" stroke-width="1.7" marker-end="url(#arrow)"/>')
        # Labels on a white backing remain readable over crossing connectors.
        label = textwrap.wrap(relation, width=16) or [""]
        y = (y1 + y2) / 2 - 8
        pieces.append(f'<rect x="{mid - 49}" y="{y - 13}" width="98" height="{len(label) * 14 + 4}" rx="3" fill="white"/>')
        for i, line in enumerate(label):
            pieces.append(f'<text x="{mid}" y="{y + i * 14}" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#526b7b">{escape(line)}</text>')
    for key, label in labels.items():
        x, y = positions[key]
        is_activity = "EXPERIMENTAL_STEP" in label
        color = "#12384b" if is_activity else "#f0f7fa"
        text_color = "white" if is_activity else "#183448"
        pieces.append(f'<g><title>{escape(label)}</title><rect x="{x}" y="{y}" width="250" height="88" rx="8" fill="{color}" stroke="#a2bdca"/>')
        wrapped = textwrap.wrap(label, width=30)
        for i, line in enumerate(wrapped):
            pieces.append(f'<text x="{x + 125}" y="{y + 44 + (i - (len(wrapped)-1)/2) * 17 + 5}" text-anchor="middle" font-family="sans-serif" font-size="13" fill="{text_color}">{escape(line)}</text>')
        pieces.append('</g>')
    return "".join(pieces) + "</svg>"


def _level_cards(source):
    """Short explanations taken from the existing levels table, not a second model."""
    import markdown

    cards, in_table = [], False
    for line in source.splitlines():
        if "| GaSi-Bedeutung |" in line:
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("| ").split("|")]
        if len(cells) >= 2 and cells[0] in ("Messlauf", "Messstufe", "Messpunkt"):
            explanation = re.split(r"(?<=[.!?])\s+", cells[1], maxsplit=1)[0]
            cards.append(f'<div class="level-card"><h3>{escape(cells[0])}</h3>{markdown.markdown(explanation)}</div>')
    return "".join(cards)


def _document_sections(body):
    """Preserve the complete document behind closed, independently expandable sections."""
    sections = []
    for part in re.split(r"(?=<h2\b)", body):
        heading = re.search(r"<h2\b[^>]*>(.*?)</h2>", part, flags=re.S)
        if heading:
            title = unescape(re.sub(r"<[^>]+>", "", heading.group(1))).replace("¶", "").strip()
        else:
            part = re.sub(r"<h1\b[^>]*>.*?</h1>", "", part, flags=re.S).strip()
            if not part:
                continue
            title = "Einordnung"
        sections.append(f'<details class="model-section"><summary>{escape(title)}</summary><div class="section-body">{part}</div></details>')
    return "".join(sections)


def render_html(source: str, source_name: str = "GaSi_Datenmodell.md", *, concept_href: str | None = None) -> str:
    import markdown

    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"toc_depth": "2-3", "permalink": True}})
    body = md.convert(source)
    diagrams = []
    technical_diagrams = []

    def diagram(match):
        raw = unescape(match.group(1))
        try:
            drawing = f'<div class="diagram">{flowchart_svg(raw)}</div>'
            technical_drawing = f'<div class="diagram">{flowchart_svg(raw, simple=False)}</div>'
            controls = ('<div class="graph-controls"><button type="button" data-zoom="out" aria-label="Grafik verkleinern">−</button>'
                '<button type="button" data-zoom="fit">Einpassen</button>'
                '<button type="button" data-zoom="in" aria-label="Grafik vergrößern">+</button>'
                '<button type="button" data-fullscreen>Vollbild</button></div>')
            graph_attr = ' data-graph'
        except ValueError as exc:
            drawing = '<p class="diagram-warning">Die Grafik lässt sich noch nicht anzeigen. Die Angaben stehen unten in den Details.</p>'
            technical_drawing = f'<p class="diagram-warning">{escape(str(exc))}</p><pre><code>{escape(raw)}</code></pre>'
            controls, graph_attr = "", ""
        simple_controls = '<div class="graph-controls"><button type="button" data-fullscreen>Größer ansehen</button></div>' if graph_attr else ""
        is_test = 'GASI_TEST_RUN_01' in raw
        title = 'openBIS: Schreibtest' if is_test else 'Das gehört zusammen'
        caption = 'Erstellungsplan des synthetischen Tests; Zielpfade und Anlage: Einmalig einrichten.' if is_test else 'Zu einer Messung können mehrere Dateien gehören.'
        figure = f'<figure{graph_attr}><div class="figure-heading"><h2>{title}</h2>{simple_controls}</div>{drawing}<figcaption class="simple-note">{caption}</figcaption></figure>'
        diagrams.append(f'<details class="relations-view"><summary>openBIS-Beziehungen des Schreibtests ansehen</summary>{figure}</details>' if is_test else figure)
        technical_diagrams.append(f'<figure{graph_attr}><div class="figure-heading"><h2>{title if is_test else "Technische Bezeichnungen"}</h2>{controls}</div>{technical_drawing}'
            '<figcaption><span class="line-key">Parent-Beziehung</span><span class="line-key dataset">Dateianhang</span>'
            '<span class="line-key property">OBJECT-Property</span></figcaption></figure>')
        return (f'<p><a href="#diagram">Beziehungsgrafik oben ansehen</a></p><details class="diagram-source">'
                f'<summary>Diagrammquelle anzeigen</summary><pre><code>{escape(raw)}</code></pre></details>')

    body = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', diagram, body, flags=re.S)
    body = re.sub(r"(<table>.*?</table>)", r'<div class="table-wrap">\1</div>', body, flags=re.S)
    title_match = re.search(r"^# (.+)$", source, flags=re.M)
    title = title_match.group(1).strip() if title_match else "GaSi-Datenmodell"
    short_title = "GaSi: aktueller Aufbau und Messung" if "GaSi" in title else title
    diagram_view = "".join(diagrams) or '<p class="diagram-warning">Die Quelle enthält noch keine Beziehungsgrafik.</p>'
    sections = _document_sections(body)
    status = '<span class="status-pill" title="Die Zuordnung muss noch fachlich bestätigt werden.">Vorschlag</span>' if "kein in openBIS registriertes Schema" in source else ""
    digest = sha256(source.encode("utf-8")).hexdigest()
    details = f'''<details id="details" class="expert-view"><summary>Mehr wissen: Technik und Quellen</summary><div class="expert-content">
<div class="detail-search"><label for="search">In den Details suchen</label><input id="search" type="search" placeholder="Suchbegriff …">
<span id="search-count" role="status" aria-live="polite"></span></div>
<div class="technical-diagrams">{''.join(technical_diagrams)}</div>
<section id="levels" class="levels" aria-label="Fachliche Ebenen">{_level_cards(source)}</section>
<section><h2 class="details-heading">Details, Felder und Quellen</h2>{sections}</section>
<footer class="source-note">Quelle: <a href="{escape(source_name, quote=True)}">{escape(source_name)}</a> · Neu erzeugen: GaSi_02_Einmalig_einrichten.ipynb (Zelle Datenmodell und HTML) → Run All.
<details><summary>Quellstand und Offline-Ansicht</summary>SHA-256: {digest}<br>
Die Markdown-Datei bleibt die maßgebliche Quelle. Die Ansicht benötigt keine Internetverbindung.</details></footer></div></details>'''
    concept_link = (f'<p><a href="{escape(concept_href, quote=True)}">Forschungsablauf: die vier BAM-Schritte ansehen →</a></p>'
                    if concept_href else "")
    return f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gasi-view" content="full"><meta name="gasi-model-sha256" content="{digest}">
<title>{escape(title)}</title><style>{STYLE}</style></head><body>
<a class="skip" href="#diagram">Zum Datenmodell</a>
<header class="toolbar"><span class="brand">GaSi · BAM / FB 8.1</span>
<button id="print" type="button">Drucken</button></header>
<div class="layout"><main id="model"><div class="hero"><h1>{escape(short_title)}</h1>{status}</div>
<article>{concept_link}<section id="diagram" aria-label="Modellübersicht">{diagram_view}</section>{details}</article>
</main></div><script>{SCRIPT}</script></body></html>
'''


def _read_model(source_path):
    source_path = Path(source_path).resolve()
    if source_path.suffix.lower() not in (".md", ".markdown"):
        raise ValueError("Als Quelle wird eine Markdown-Datei (.md oder .markdown) benötigt.")
    return source_path, source_path.read_bytes().decode("utf-8")


def _generate_concept_view(source_path):
    """Keep notebook/CLI regeneration in one place; no second command required."""
    concept_source = source_path.with_name("GaSi_Konzeptmodell.md")
    if not concept_source.is_file():
        return None
    import importlib
    import gasi_concept_html
    current = importlib.reload(gasi_concept_html)
    return current.generate_concept_html(concept_source).name


def generate_html(source_path: str | Path = SOURCE) -> Path:
    """Full reference view; kept for callers that need the complete document."""
    source_path, source = _read_model(source_path)
    concept_href = _generate_concept_view(source_path)
    document = render_html(source, source_path.name, concept_href=concept_href).replace(
        '<details id="details" class="expert-view">', '<details id="details" class="expert-view" open>')
    output = source_path.with_suffix(".html")
    output.write_text(document, encoding="utf-8", newline="\n")
    return output


def show_model_export_button(repo_root: str | Path = ROOT):
    """Optional notebook UI: absence of these extras never breaks offline CSV checks."""
    root = Path(repo_root).resolve()
    try:
        import markdown  # noqa: F401 -- check before presenting an unusable button
        import ipywidgets as widgets
        from IPython.display import FileLink, display
    except ImportError:
        print(f"HTML-Knopf: Zusatzpakete fehlen im aktiven Python: {sys.executable}")
        print("In einer Notebook-Zelle für genau diesen Kernel installieren:")
        print(f'%pip install -r "{root / "requirements-docs.txt"}"')
        print("Danach den Kernel neu starten und Run All ausführen. Alternativ oben rechts die Projekt-.venv wählen.")
        return None
    button = widgets.Button(description="Datenmodell als HTML erzeugen", icon="file-code-o",
                            layout=widgets.Layout(width="310px"), button_style="info")
    output = widgets.Output()

    def regenerate(_):
        button.disabled = True
        with output:
            output.clear_output(wait=True)
            try:
                # Also refresh the renderer when an already displayed button is reused.
                import importlib
                current = importlib.reload(sys.modules[__name__])
                detailed = current.generate_html(root / "docs" / "GaSi_Datenmodell.md")
                concept = detailed.with_name("GaSi_Konzeptmodell.html")
                path = concept if concept.is_file() else detailed
                print("Datenmodell-HTML und vorhandene Konzeptgrafiken neu erzeugt.")
                display(FileLink(path.relative_to(root).as_posix(), result_html_prefix="Datenmodell öffnen: "))
            except (OSError, ValueError) as exc:
                print(f"HTML konnte nicht erzeugt werden: {exc}")
            finally:
                button.disabled = False

    button.on_click(regenerate)
    widget = widgets.VBox([button, output])
    display(widget)
    return widget


def main() -> int:
    parser = argparse.ArgumentParser(description="GaSi-Markdown-Datenmodell lokal als HTML erzeugen")
    parser.add_argument("--source", type=Path, default=SOURCE, help="Markdown-Quelle; HTML wird daneben erzeugt")
    args = parser.parse_args()
    try:
        detailed = generate_html(args.source)
        concept = detailed.with_name("GaSi_Konzeptmodell.html")
        print(concept if concept.is_file() else detailed)
    except ImportError:
        parser.exit(1, "HTML-Export benötigt: python -m pip install -r requirements-docs.txt\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"HTML-Export fehlgeschlagen: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
