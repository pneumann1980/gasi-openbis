"""Conceptual workflow topology, offline regeneration and diagram legibility."""
from hashlib import sha256
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from gasi_concept_html import concept_svg, render_concept_html
from gasi_model_html import generate_simple_html
from tests.test_model_html import Page, VisibleText


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/GaSi_Konzeptmodell.md"


def graphs(source):
    return re.findall(r"```mermaid\s*\n(.*?)```", source, re.S)


class ConceptTests(unittest.TestCase):
    def test_four_bam_steps_are_accessible_and_long_details_are_closed(self):
        source = SOURCE.read_text(encoding="utf-8")
        html = render_concept_html(source)
        page = Page(html)
        self.assertEqual(page.diagrams, 3)
        self.assertFalse(page.scripts, "No external scripts or Mermaid CDN")
        self.assertTrue({f"schritt-{n}" for n in range(1, 5)}.issubset(page.ids))
        self.assertTrue(set(page.anchors).issubset(page.ids))
        for term in ("Draw the research workflow", "Identify Entities and Entity types",
                     "Map the research workflow", "Connect Entities"):
            self.assertIn(term, html)
        self.assertNotRegex(html, r"<details[^>]*\bopen\b")
        self.assertNotIn("Seriennummer als belegte Identität", " ".join(VisibleText(html).text))
        self.assertIn(sha256(source.encode("utf-8")).hexdigest(), html)

    def test_all_source_edges_and_nodes_render_without_crossings_or_overlapping_boxes(self):
        for graph in graphs(SOURCE.read_text(encoding="utf-8")):
            svg = ET.fromstring(concept_svg(graph))
            nodes = {n.attrib["data-node"] for n in svg.iter() if "data-node" in n.attrib}
            source_nodes = set(re.findall(r"\b([A-Za-z]\w*)\[", graph))
            edges = { (n.attrib["data-source"], n.attrib["data-target"])
                     for n in svg.iter() if "data-source" in n.attrib }
            source_edges = set(re.findall(r"([A-Za-z]\w*)(?:\[[^\]]+\])?\s*-->\s*\|[^|]+\|\s*([A-Za-z]\w*)", graph))
            self.assertEqual(nodes, source_nodes)
            self.assertEqual(edges, source_edges)
            boxes = [tuple(float(n.attrib[k]) for k in ("x", "y", "width", "height"))
                     for n in svg.iter() if n.attrib.get("class") == "node-box"]
            for i, (x, y, w, h) in enumerate(boxes):
                for xx, yy, ww, hh in boxes[i+1:]:
                    self.assertFalse(max(x, xx) < min(x+w, xx+ww) and max(y, yy) < min(y+h, yy+hh))
            segments = []
            for n in svg.iter():
                if n.attrib.get("class") != "connection":
                    continue
                tokens = re.findall(r"[MHV]|[\d.]+", n.attrib["d"])
                px, py = map(float, tokens[1:3])
                for i in range(3, len(tokens), 2):
                    value = float(tokens[i+1])
                    nx, ny = (value, py) if tokens[i] == "H" else (px, value)
                    segments.append((px, py, nx, ny))
                    for x, y, w, h in boxes:
                        crosses = (y < py < y+h and max(min(px,nx),x) < min(max(px,nx),x+w)) if py == ny else (x < px < x+w and max(min(py,ny),y) < min(max(py,ny),y+h))
                        self.assertFalse(crosses, "Line crosses box")
                    px, py = nx, ny
            for i, (x1, y1, x2, y2) in enumerate(segments):
                for a1, b1, a2, b2 in segments[i+1:]:
                    if y1 == y2 and b1 == b2:
                        self.assertFalse(y1 == b1 and max(min(x1,x2),min(a1,a2)) < min(max(x1,x2),max(a1,a2)))
                    elif x1 == x2 and a1 == a2:
                        self.assertFalse(x1 == a1 and max(min(y1,y2),min(b1,b2)) < min(max(y1,y2),max(b1,b2)))
                    else:
                        h, v = ((x1,y1,x2,y2),(a1,b1,a2,b2)) if y1 == y2 else ((a1,b1,a2,b2),(x1,y1,x2,y2))
                        self.assertFalse(min(h[0],h[2]) < v[0] < max(h[0],h[2]) and min(v[1],v[3]) < h[1] < max(v[1],v[3]))

    def test_source_changes_never_silently_drop_entities_or_replace_relationship_semantics(self):
        source = SOURCE.read_text(encoding="utf-8")
        workflow, _, relations = graphs(source)
        for broken in (workflow + "\nE -->|erzeugt| NEW[Neues Ergebnis]",
                       workflow.replace("M -->|danach| E", "M -->|danach| DP"),
                       relations.replace("|Parent|", "|Dataset attachment|", 1)):
            with self.assertRaises(ValueError):
                concept_svg(broken)
        changed = workflow.replace("Ergebnisse beurteilen", "Neue Ergebnisse")
        self.assertIn("Neue Ergebnisse", concept_svg(changed))
        self.assertNotIn("Ergebnisse beurteilen", concept_svg(changed))

    def test_existing_notebook_entrypoint_regenerates_companion_and_standalone_svgs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / "GaSi_Datenmodell.md"
            concept = root / SOURCE.name
            model.write_bytes((ROOT / "docs/GaSi_Datenmodell.md").read_bytes())
            # Windows checkout must retain the hash of the actual CRLF source.
            original = SOURCE.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            concept.write_bytes(original)
            simple = generate_simple_html(model)
            self.assertIn('href="GaSi_Konzeptmodell.html"', simple.read_text(encoding="utf-8"))
            first = concept.with_suffix(".html").read_bytes()
            self.assertIn(sha256(original).hexdigest().encode("ascii"), first)
            for kind in ("workflow", "mapping", "relations"):
                svg = root / f"GaSi_Konzeptmodell_{kind}.svg"
                self.assertTrue(svg.exists())
                ET.fromstring(svg.read_text(encoding="utf-8"))
            self.assertEqual(concept.read_bytes(), original)
            generate_simple_html(model)
            self.assertEqual(first, concept.with_suffix(".html").read_bytes())
            concept.write_text(original.decode("utf-8").replace("Ergebnisse beurteilen", "Neue Ergebnisse"), encoding="utf-8")
            generate_simple_html(model)
            self.assertIn("Neue Ergebnisse", concept.with_suffix(".html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
