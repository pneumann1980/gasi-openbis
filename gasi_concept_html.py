"""Four views of the conceptual model, from Markdown, without network access.

Fixed diagram lanes keep connectors out of boxes. The source supplies every
caption and relationship; a changed topology is rejected rather than omitted.
"""
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
import re
import textwrap


def _profile(kind):
    if kind == "workflow":
        boxes = {
            "P": (40, 45, 320, 100), "M": (490, 45, 320, 100), "E": (940, 45, 320, 100),
            "DP": (40, 255, 320, 100), "DM": (490, 255, 320, 100), "DE": (940, 255, 320, 100),
        }
        routes = {
            ("P", "M"): "M360 95 H490", ("M", "E"): "M810 95 H940",
            ("P", "DP"): "M200 145 V255", ("M", "DM"): "M650 145 V255", ("E", "DE"): "M1100 145 V255",
        }
        return (1300, 390), boxes, routes
    if kind == "mapping":
        rows = [("LS", "LP", "LC", "LO", "LD"), ("IS", "IP", "IC", "IO"), ("GS", "GP", "GC", "GO")]
        boxes, routes = {}, {}
        for row, keys in enumerate(rows):
            y = 35 + row * 180
            for col, key in enumerate(keys):
                boxes[key] = (25 + col * 260, y, 220, 115)
            for start, end in zip(keys, keys[1:]):
                x, _, w, h = boxes[start]
                routes[start, end] = f"M{x+w} {y+h/2} H{boxes[end][0]}"
        return (1320, 540), boxes, routes
    if kind == "relations":
        boxes = {
            "Q": (60, 45, 200, 110), "I": (340, 45, 200, 110), "G": (570, 45, 200, 110),
            "D": (800, 45, 200, 110), "W": (1080, 45, 200, 110),
            "P": (60, 350, 200, 100), "M": (590, 350, 220, 100), "E": (1080, 350, 200, 100),
        }
        routes = {
            ("Q", "P"): "M160 155 V350", ("P", "M"): "M260 400 H590",
            ("M", "E"): "M810 400 H1080", ("I", "M"): "M440 155 V225 H630 V350",
            ("G", "M"): "M670 155 V350", ("D", "M"): "M900 155 V250 H750 V350",
            ("W", "E"): "M1180 155 V350",
        }
        return (1340, 490), boxes, routes
    if kind == "combined":
        boxes = {
            "IS": (130, 90, 240, 60), "IP": (130, 190, 240, 60), "IC": (130, 290, 240, 60),
            "LS": (440, 90, 810, 60), "LP": (440, 190, 810, 60),
            "PC": (450, 290, 220, 60), "MC": (740, 290, 220, 60), "EC": (1030, 290, 220, 60),
            "RS": (1310, 90, 240, 60), "RP": (1310, 190, 240, 60), "RC": (1310, 290, 240, 60),
            "I": (140, 540, 230, 100), "P": (450, 540, 220, 100),
            "M": (740, 540, 220, 100), "E": (1030, 540, 220, 100),
            "Q": (1320, 400, 220, 70), "G": (1320, 540, 220, 70),
            "W": (1320, 700, 220, 70), "D": (1320, 840, 220, 70),
            "DP": (450, 980, 220, 90), "DM": (740, 980, 220, 90), "DE": (1030, 980, 220, 90),
        }
        routes = {
            ("IS", "IP"): "M250 150 V190", ("IP", "IC"): "M250 250 V290",
            ("LS", "LP"): "M845 150 V190", ("LP", "PC"): "M560 250 V290",
            ("LP", "MC"): "M850 250 V290", ("LP", "EC"): "M1140 250 V290",
            ("RS", "RP"): "M1430 150 V190", ("RP", "RC"): "M1430 250 V290",
            ("Q", "P"): "M1320 435 H560 V540", ("P", "M"): "M670 590 H740",
            ("M", "E"): "M960 590 H1030", ("I", "M"): "M370 590 H410 V820 H780 V640",
            ("G", "M"): "M1320 575 H1280 V500 H850 V540",
            ("W", "E"): "M1320 735 H1280 V615 H1250",
            ("D", "M"): "M1320 875 H950 V640",
        }
        return (1600, 1110), boxes, routes
    raise ValueError(f"Unbekannte Konzeptgrafik: {kind}")


def concept_svg(source):
    """Validate the supported graph in full before rendering its orthogonal lanes."""
    profile = re.search(r"^\s*%% gasi-view: (\w+)\s*$", source, re.M)
    if not profile:
        raise ValueError("Konzeptgrafik benötigt eine gasi-view-Angabe.")
    kind = profile.group(1)
    (width, height), boxes, routes = _profile(kind)
    node = r"([A-Za-z]\w*)(?:\[([^\]]+)\])?"
    edge = re.compile(rf"{node}\s*-->\s*\|([^|]+)\|\s*{node}")
    labels, edges = {}, {}
    lines = [s.strip() for s in source.splitlines() if s.strip() and not s.strip().startswith("%%")]
    if not lines or lines[0] != "flowchart LR":
        raise ValueError("Konzeptgrafik benötigt flowchart LR.")
    for line in lines[1:]:
        match = edge.fullmatch(line)
        if not match:
            single = re.fullmatch(node, line)
            if not single or not single.group(2):
                raise ValueError("Nicht unterstützte Konzeptgrafik-Syntax.")
            key, label = single.groups()
            if key in labels and labels[key] != label:
                raise ValueError("Widersprüchliche Beschriftung in der Konzeptgrafik.")
            labels[key] = label
            continue
        start, left, relation, end, right = match.groups()
        if (start, end) in edges:
            raise ValueError("Doppelte Beziehung in der Konzeptgrafik.")
        for key, label in ((start, left), (end, right)):
            if label and key in labels and labels[key] != label:
                raise ValueError("Widersprüchliche Beschriftung in der Konzeptgrafik.")
            if label:
                labels[key] = label
        edges[start, end] = relation
    if set(labels) != set(boxes) or set(edges) != set(routes):
        raise ValueError("Konzeptgrafik wurde strukturell geändert; Diagrammlayout zuerst anpassen.")
    for pair, relation in edges.items():
        expected = None
        if kind == "relations":
            expected = "Parent"
        elif kind == "combined":
            expected = "enthält" if pair[0] in {"IS", "IP", "LS", "LP", "RS", "RP"} else "Parent"
        if expected and relation != expected:
            raise ValueError("Beziehungsart passt nicht zur Ebene der Konzeptgrafik.")

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" data-profile="{kind}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="{kind}-title">',
        f'<title id="{kind}-title">GaSi: {dict(workflow="Forschungsablauf", mapping="Ablage in openBIS", relations="Objektbeziehungen", combined="Gesamtmodell nach BAM-Vorlage")[kind]}</title>',
        f'<defs><marker id="{kind}-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0 L8 4 L0 8 Z" fill="#527889"/></marker></defs>',
    ]
    if kind == "combined":
        for x, w, label in ((130, 240, "FB-8.1-Geräteinventar"), (440, 810, "Laborbuch"), (1310, 240, "Weitere Ressourcen")):
            parts.append(f'<rect x="{x}" y="20" width="{w}" height="35" fill="#163f50"/><text x="{x+w/2}" y="44" text-anchor="middle" font-family="sans-serif" font-size="17" fill="white">{label}</text>')
        for y, h, label, color in ((90,60,"SPACE","#e9eef5"),(190,60,"PROJECT","#e8f4e9"),(290,60,"COLLECTION","#fff4d6"),(400,510,"OBJECT","#e4effb"),(980,90,"DATASET","#f2eafb")):
            parts.append(f'<rect x="8" y="{y}" width="110" height="{h}" fill="{color}"/><text x="63" y="{y+min(h/2,42)}" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#173b4c">{label}</text>')
        for x in (400, 1270):
            parts.append(f'<path d="M{x} 65 V1060" stroke="#b9cdd6" stroke-dasharray="5 5" fill="none"/>')
    for (start, end), path in routes.items():
        relation = edges[start, end]
        dash = ' stroke-dasharray="5 4"' if kind == "combined" and relation == "enthält" else ""
        parts.append(f'<path class="connection" data-source="{start}" data-target="{end}" data-relation="{escape(relation, quote=True)}" d="{path}" fill="none" stroke="#527889" stroke-width="2"{dash} marker-end="url(#{kind}-arrow)"><title>{escape(relation)}</title></path>')
        # Labels are in free lanes, never on the connectors or a node.
        if kind == "workflow":
            x, y, w, h = boxes[start]
            tx, ty = ((x+w+65, y+h/2-12) if start in ("P", "M") and end in ("M", "E")
                      else (x+w/2+40, y+h+55))
            parts.append(f'<text x="{tx}" y="{ty}" text-anchor="middle" font-size="14" fill="#496777">{escape(relation)}</text>')
        if kind == "relations" and (start, end) in (("P", "M"), ("M", "E")):
            x, y, w, h = boxes[start]
            tx = (x+w+boxes[end][0])/2
            parts.append(f'<text x="{tx}" y="{y+h/2-14}" text-anchor="middle" font-size="16" fill="#496777">Parent → Child</text>')
    for key, label in labels.items():
        x, y, w, h = boxes[key]
        activity = kind in ("workflow", "relations", "combined") and key in ("P", "M", "E")
        fill, ink = ("#163f50", "#ffffff") if activity else ("#edf5f8", "#173b4c")
        if kind == "mapping":
            fill = {"S": "#e9eef5", "P": "#e8f4e9", "C": "#fff4d6", "O": "#e4effb", "D": "#f2eafb"}[key[1]]
        if kind == "combined" and not activity:
            y = boxes[key][1]
            fill = ("#e9eef5" if y == 90 else "#e8f4e9" if y == 190 else
                    "#fff4d6" if y == 290 else "#f2eafb" if key in {"DP","DM","DE"} else "#e4effb")
        parts.append(f'<g data-node="{key}"><title>{escape(label)}</title><rect class="node-box" x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="#b3cbd6"/>')
        title, _, subtitle = label.partition(" / ")
        heading = textwrap.wrap(title, width=max(14, int(w/10)))
        detail = textwrap.wrap(subtitle, width=max(16, int(w/8)))
        lines = [(s, 18, True) for s in heading] + [(s, 14, False) for s in detail]
        if len(lines) * 21 > h - 12:
            raise ValueError(f"Beschriftung zu lang für Konzeptgrafik: {key}")
        for i, (line, size, bold) in enumerate(lines):
            ty = y+h/2+(i-(len(lines)-1)/2)*21+5
            parts.append(f'<text x="{x+w/2}" y="{ty}" text-anchor="middle" font-family="sans-serif" font-size="{size}" font-weight="{600 if bold else 400}" fill="{ink}">{escape(line)}</text>')
        parts.append("</g>")
    return "".join(parts) + "</svg>"


STYLE = """
:root{font:18px/1.5 system-ui,sans-serif;color:#183a4b;background:#f4f7f8}
*{box-sizing:border-box}body{margin:0}header,main,footer{max-width:1400px;margin:auto;padding:16px 26px}
header{display:flex;justify-content:space-between;gap:12px;align-items:center}a{color:#075e82}
h1{font-size:1.65rem;margin:8px 0}h2{font-size:1.35rem;margin:12px 0}p{max-width:85ch}
.intro{font-size:.9rem}nav{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
nav a{padding:10px 18px;background:white;border:1px solid #b6ccd7;border-radius:8px;text-decoration:none}
nav a[aria-current=step]{background:#163f50;color:white}
.step{background:white;padding:18px 24px;border:1px solid #d4e0e6;border-radius:12px}
.step[hidden]{display:none}figure{margin:8px 0 16px}figure .drawing{overflow:auto}
svg{display:block;width:100%;min-width:850px;max-height:62vh}figcaption{font-size:.85rem}
svg[data-profile=combined]{max-height:none;min-width:1200px}
details{margin:12px 0;border-top:1px solid #d9e5ea;padding:10px 0}
summary{cursor:pointer;color:#125570}table{border-collapse:collapse;font-size:.88rem;width:100%}
td,th{padding:9px 11px;border-bottom:1px solid #d9e5ea;text-align:left;vertical-align:top}
th{background:#edf5f8}.table-scroll{overflow:auto}code{font-size:.9em;overflow-wrap:anywhere}
footer{font-size:.85rem}button{font:inherit;cursor:pointer;padding:5px 12px}
figure:fullscreen{background:white;padding:24px;overflow:auto}figure:fullscreen svg{max-height:85vh}
@media(max-width:650px){header,main,footer{padding:12px}.step{padding:12px}h1{font-size:1.3rem}}
@media print{nav,button{display:none}.step[hidden]{display:block}.step{break-before:page}svg{min-width:0;max-height:none}details>*{display:block!important}}
"""

SCRIPT = """
const links = [...document.querySelectorAll('nav a')];
const panels = [...document.querySelectorAll('.step')];
function select() {
  const id = panels.some(p => '#'+p.id === location.hash) ? location.hash : '#schritt-1';
  panels.forEach(p => { p.hidden = '#'+p.id !== id; });
  links.forEach(a => {
    if (a.hash === id) a.setAttribute('aria-current','step');
    else a.removeAttribute('aria-current');
  });
}
window.addEventListener('hashchange',select);select();
document.querySelectorAll('[data-fullscreen]').forEach(b => {
  if (!document.fullscreenEnabled) { b.hidden = true; return; }
  b.addEventListener('click',() => b.closest('figure').requestFullscreen().catch(()=>{}));
});
document.querySelector('[data-print]').addEventListener('click',() => {
  const states = [...document.querySelectorAll('details')].map(d => [d,d.open]);
  document.querySelectorAll('details').forEach(d => { d.open = true; });
  window.print();states.forEach(([d,open]) => { d.open = open; });
});
"""


def render_concept_html(source, source_name="GaSi_Konzeptmodell.md"):
    import markdown
    sections = re.split(r"^## ([1-4]\. .+)$", source, flags=re.M)
    if len(sections) != 9:
        raise ValueError("Das Konzeptmodell benötigt genau die vier BAM-Schritte.")
    diagrams = re.findall(r"```mermaid\s*\n(.*?)```", source, re.S)
    kinds = [re.search(r"%% gasi-view: (\w+)", raw).group(1) for raw in diagrams]
    if kinds != ["workflow", "mapping", "combined", "relations"]:
        raise ValueError("Konzeptmodell benötigt Ablauf-, Ablage-, Gesamt- und Beziehungsgrafik.")

    def diagram(match):
        raw = unescape(match.group(1))
        svg = concept_svg(raw)
        kind = re.search(r"%% gasi-view: (\w+)", raw).group(1)
        filename = Path(source_name).stem + "_" + kind + ".svg"
        return (f'<figure><button type="button" data-fullscreen>Größer ansehen</button> '
                f'<a href="{escape(filename, quote=True)}" download>SVG herunterladen</a><div class="drawing">{svg}</div></figure>')

    body = []
    for index, (title, content) in enumerate(zip(sections[1::2], sections[2::2]), 1):
        rendered = markdown.markdown(content, extensions=["tables", "fenced_code", "md_in_html", "sane_lists"])
        rendered = re.sub(r'<pre><code class="language-mermaid">(.*?)</code></pre>', diagram, rendered, flags=re.S)
        rendered = re.sub(r"(<table>.*?</table>)", r'<div class="table-scroll">\1</div>', rendered, flags=re.S)
        body.append(f'<section class="step" id="schritt-{index}"><h2>{escape(title)}</h2>{rendered}</section>')
    digest = sha256(source.encode("utf-8")).hexdigest()
    # The authored introduction carries scope/provenance and is kept in the page.
    intro = markdown.markdown(sections[0])
    return f'''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gasi-concept-sha256" content="{digest}"><title>GaSi: Konzeptmodell in vier Schritten</title>
<style>{STYLE}</style></head><body>
<header><a href="GaSi_Datenmodell_einfach.html">Geräteübersicht</a><span>BAM · FB 8.1</span><button type="button" data-print>Drucken</button></header>
<main><div class="intro">{intro}</div><nav aria-label="Die vier BAM-Schritte">
<a href="#schritt-1">1 · Ablauf</a><a href="#schritt-2">2 · Bausteine</a>
<a href="#schritt-3">3 · Ablage</a><a href="#schritt-4">4 · Verbindungen</a></nav>
{"".join(body)}</main><footer>Offline erzeugt aus <a href="{escape(source_name, quote=True)}">{escape(source_name)}</a>.
Neu erzeugen: Notebook 01 → Run All. <a href="GaSi_Datenmodell.html#details">Fachliche Details und Instanzbefund</a>.</footer>
<script>{SCRIPT}</script></body></html>'''


def generate_concept_html(source_path):
    """Read the source anew on every run; export the same diagrams as standalone SVG."""
    source_path = Path(source_path).resolve()
    source = source_path.read_bytes().decode("utf-8")
    document = render_concept_html(source, source_path.name)
    diagrams = re.findall(r"```mermaid\s*\n(.*?)```", source, re.S)
    exports = {source_path.with_suffix(".html"): document}
    for raw in diagrams:
        kind = re.search(r"%% gasi-view: (\w+)", raw).group(1)
        exports[source_path.with_name(source_path.stem + "_" + kind + ".svg")] = concept_svg(raw)
    for path, value in exports.items():
        path.write_text(value, encoding="utf-8", newline="\n")
    return source_path.with_suffix(".html")
