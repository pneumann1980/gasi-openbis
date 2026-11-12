"""The HTML must track the current model, including button-driven regeneration."""
from contextlib import redirect_stdout
from hashlib import sha256
from html.parser import HTMLParser
import io
import re
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from gasi_model_html import SOURCE, flowchart_svg, generate_html, generate_simple_html, render_html, show_model_export_button


class Page(HTMLParser):
    def __init__(self, value):
        super().__init__()
        self.ids, self.anchors, self.scripts = set(), [], []
        self.tables = self.diagrams = 0
        self.model_sections = []
        self.feed(value)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.anchors.append(attrs["href"][1:])
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        self.tables += tag == "table"
        self.diagrams += tag == "svg"
        if tag == "details" and attrs.get("class") == "model-section":
            self.model_sections.append(attrs)


class VisibleText(HTMLParser):
    """Text visible without opening details (SVG titles are tooltips, not captions)."""
    def __init__(self, html):
        super().__init__()
        self.stack, self.text = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        if tag not in {"br", "input", "meta", "link", "hr", "img"}:
            self.stack.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if any(tag in {"head", "script", "style", "title", "desc"} for tag, _ in self.stack):
            return
        for i, (tag, attrs) in enumerate(self.stack):
            if tag == "details" and "open" not in attrs:
                if len(self.stack) <= i+1 or self.stack[i+1][0] != "summary":
                    return
        self.text.append(data)


class HtmlModelTests(unittest.TestCase):
    def test_current_model_has_tables_valid_navigation_and_offline_diagram(self):
        source = SOURCE.read_bytes().decode("utf-8")
        html = render_html(source)
        page = Page(html)
        self.assertGreaterEqual(page.tables, 5)
        self.assertEqual(page.diagrams, 4)
        self.assertTrue(set(page.anchors).issubset(page.ids))
        self.assertFalse(page.scripts)
        for value in ("EXPERIMENTAL_STEP", "RAW_DATA", "GAS_BOTTLE", "CALIBRATION", "Quellen", "Beleggrenzen"):
            self.assertIn(value, html)
        self.assertIn('../data/wiki/home.txt', html)
        self.assertIn(sha256(source.encode("utf-8")).hexdigest(), html)

    def test_compact_overview_keeps_details_closed_and_preserves_all_relations(self):
        source = SOURCE.read_text(encoding="utf-8")
        html = render_html(source)
        page = Page(html)
        self.assertGreater(len(page.model_sections), 5)
        self.assertTrue(all("open" not in section for section in page.model_sections))
        self.assertLess(html.index('<section id="diagram"'), html.index('<details id="details"'))
        self.assertNotIn("<aside", html)
        self.assertIn('data-zoom="fit"', html)
        self.assertIn('data-fullscreen', html)
        graph = re.search(r"```mermaid\s*\n(.*?)```", source, re.S).group(1)
        svg = ET.fromstring(flowchart_svg(graph))
        nodes = {node.attrib["data-node"] for node in svg.iter() if "data-node" in node.attrib}
        edges = {(node.attrib["data-source"], node.attrib["data-target"]) for node in svg.iter() if "data-source" in node.attrib}
        self.assertEqual(nodes, {"A", "M", "G", "I", "D", "S", "R", "CSV", "CFG", "RES", "C"})
        self.assertEqual(edges, {("A", "M"), ("M", "I"), ("I", "S"), ("G", "R"), ("I", "R"), ("D", "R"), ("S", "R"),
                                 ("R", "CSV"), ("R", "CFG"), ("R", "RES"), ("C", "I")})

    def test_simple_view_uses_laboratory_words_and_lines_do_not_cross_boxes(self):
        source = SOURCE.read_text(encoding="utf-8")
        html = render_html(source)
        visible = " ".join(VisibleText(html).text)
        self.assertLess(len(visible.split()), 105)
        for term in ("GaSi-Anlage", "Module", "Geräte", "Aktueller Aufbau", "Prüfgas", "Prüfling", "Messung", "Messwerte", "Einstellungen", "Auswertung"):
            self.assertIn(term, visible)
        for term in ("EXPERIMENTAL_STEP", "RAW_DATA", "Dataset", "Parent", "OBJECT", "DUT", "SOP"):
            self.assertNotIn(term, visible)
        graphs = re.findall(r"```mermaid\s*\n(.*?)```", source, re.S)
        for graph in graphs:
            svg = ET.fromstring(flowchart_svg(graph))
            boxes = [tuple(float(n.attrib[k]) for k in ("x", "y", "width", "height"))
                     for n in svg.iter() if n.attrib.get("class") == "node-box"]
            for i, (x, y, w, h) in enumerate(boxes):
                for xx, yy, ww, hh in boxes[i+1:]:
                    self.assertFalse(max(x, xx) < min(x+w, xx+ww) and max(y, yy) < min(y+h, yy+hh), "Boxes overlap")
            connections = [n for n in svg.iter() if n.attrib.get("class") == "connection"]
            self.assertEqual(len(connections), 6)  # Each diagram has six visible connections.
            segments = []
            for connection in connections:
                tokens = re.findall(r"[MHV]|[\d.]+", connection.attrib["d"])
                self.assertEqual(tokens[0], "M")
                px, py = map(float, tokens[1:3])
                for i in range(3, len(tokens), 2):
                    command, value = tokens[i], float(tokens[i+1])
                    nx, ny = (value, py) if command == "H" else (px, value)
                    segments.append((px, py, nx, ny))
                    for x, y, w, h in boxes:
                        crosses = (y < py < y+h and max(min(px,nx),x) < min(max(px,nx),x+w)) if py == ny else (x < px < x+w and max(min(py,ny),y) < min(max(py,ny),y+h))
                        self.assertFalse(crosses, "Line crosses a box")
                    px, py = nx, ny
            for i, (x1,y1,x2,y2) in enumerate(segments):
                for a1,b1,a2,b2 in segments[i+1:]:
                    if y1 == y2 and b1 == b2:
                        self.assertFalse(y1 == b1 and max(min(x1,x2),min(a1,a2)) < min(max(x1,x2),max(a1,a2)), "Lines overlap")
                    elif x1 == x2 and a1 == a2:
                        self.assertFalse(x1 == a1 and max(min(y1,y2),min(b1,b2)) < min(max(y1,y2),max(b1,b2)), "Lines overlap")
                    else:
                        horizontal, vertical = ((x1,y1,x2,y2),(a1,b1,a2,b2)) if y1 == y2 else ((a1,b1,a2,b2),(x1,y1,x2,y2))
                        hx,hy,hxx,_ = horizontal
                        vx,vy,_,vyy = vertical
                        self.assertFalse(min(hx,hxx) < vx < max(hx,hxx) and min(vy,vyy) < hy < max(vy,vyy), "Lines cross")

    def test_regeneration_reads_new_content_and_leaves_markdown_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "Neues Modell.md"
            source.write_bytes(b"# First model\r\n\r\n## Fields\r\nOriginal text.\r\n")
            original = source.read_bytes()
            output = generate_html(source)
            first = output.read_bytes()
            self.assertEqual(source.read_bytes(), original)
            self.assertIn(sha256(original).hexdigest(), first.decode("utf-8"))
            self.assertEqual(generate_html(source).read_bytes(), first)
            source.write_text("# Revised model\n\n## New fields\nChanged text.", encoding="utf-8")
            self.assertEqual(generate_html(source), output)
            second = output.read_text(encoding="utf-8")
            self.assertIn("Changed text.", second)
            self.assertNotIn("Original text.", second)

    def test_button_reloads_source_on_every_click(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            source = root / "docs/GaSi_Datenmodell.md"
            source.write_text("# First click\n\nOriginal.", encoding="utf-8")
            with patch("IPython.display.display"), redirect_stdout(io.StringIO()):
                widget = show_model_export_button(root)
                button = widget.children[0]
                button.click()
                output = source.with_name(source.stem + "_einfach.html")
                self.assertIn("First click", output.read_text(encoding="utf-8"))
                source.write_text("# Second click\n\nNew source content.", encoding="utf-8")
                button.click()
                self.assertIn("Second click", output.read_text(encoding="utf-8"))
                self.assertIn("New source content.", source.with_suffix(".html").read_text(encoding="utf-8"))
                self.assertFalse(button.disabled)
            widget.close()

    def test_simple_file_contains_only_overview_and_links_to_separate_full_text(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "GaSi_Datenmodell.md"
            source.write_bytes(SOURCE.read_bytes())
            output = generate_simple_html(source)
            self.assertEqual(output.name, "GaSi_Datenmodell_einfach.html")
            simple = output.read_text(encoding="utf-8")
            full = source.with_suffix(".html").read_text(encoding="utf-8")
            self.assertEqual(Page(simple).diagrams, 2)
            self.assertEqual(Page(simple).tables, 0)
            self.assertNotIn("Ziel und Beleggrenzen", simple)
            self.assertIn('href="GaSi_Datenmodell.html#details"', simple)
            self.assertIn('name="gasi-view" content="simple"', simple)
            self.assertIn('class="expert-view" open', full)
            self.assertIn("Ziel und Beleggrenzen", full)
            self.assertLess(len(simple), len(full) / 2)

    def test_notebook_generation_cell_reloads_even_with_cached_old_generator(self):
        import nbformat
        import gasi_model_html
        from unittest.mock import Mock

        notebook = nbformat.read(SOURCE.parents[1] / "GaSi_01_Datenmodell_HTML_erzeugen.ipynb", as_version=4)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp:
            source = Path(temp) / "Model.md"
            source.write_text("# Current model\n\nCurrent content.", encoding="utf-8")
            namespace = {"Path": Path, "model_source": source, "display": Mock(), "FileLink": Mock()}
            stale = Mock(side_effect=AssertionError("Cached generator must not be called"))
            with patch.object(gasi_model_html, "generate_simple_html", stale), redirect_stdout(io.StringIO()):
                exec(notebook.cells[-1].source, namespace)
            stale.assert_not_called()
            self.assertTrue(source.with_name("Model_einfach.html").is_file())

    def test_unsupported_mermaid_remains_visible_instead_of_a_wrong_graph(self):
        html = render_html("# Model\n\n```mermaid\nsequenceDiagram\nA->>B: New syntax\n```\n")
        self.assertIn("sequenceDiagram", html)
        self.assertIn("diagram-warning", html)
        self.assertEqual(Page(html).diagrams, 0)
        with self.assertRaises(ValueError):
            flowchart_svg("flowchart LR\nA[One] --> B[Two]\nB --> A")

    def test_actual_write_relationships_are_visible_separately_from_model_proposal(self):
        source = SOURCE.read_text(encoding="utf-8")
        graph = re.findall(r"```mermaid\s*\n(.*?)```", source, re.S)[1]
        svg = ET.fromstring(flowchart_svg(graph))
        edges = {(n.attrib["data-source"], n.attrib["data-target"]) for n in svg.iter() if "data-source" in n.attrib}
        self.assertEqual(edges, {("IC", "TI"), ("LC", "TR"), ("LC", "TD"), ("TI", "TR"), ("TR", "TD"), ("TD", "TF")})
        self.assertIn("Parent → Child", "".join(svg.itertext()))
        self.assertIn("GASI_TEST_RUN_01", "".join(svg.itertext()))
        html = render_html(source, details_href="GaSi_Datenmodell.html#details")
        self.assertIn('<details class="relations-view"><summary>openBIS-Beziehungen', html)
        self.assertNotIn('<details class="relations-view" open', html)
        self.assertIn("Erstellungsplan", html)


if __name__ == "__main__":
    unittest.main()
