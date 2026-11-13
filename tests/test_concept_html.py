"""Conceptual workflow topology, offline regeneration and diagram legibility."""
from hashlib import sha256
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from gasi_concept_html import concept_svg, render_concept_html
from gasi_model_html import generate_html
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
        self.assertEqual(page.diagrams, 4)
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
                    if svg.attrib.get("data-profile")!="combined" or n.attrib.get("data-relation")=="Parent":
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
        workflow, _, combined, relations = graphs(source)
        for broken in (workflow + "\nE -->|erzeugt| NEW[Neues Ergebnis]",
                       workflow.replace("C -->|gibt Sollbedingungen vor| M", "C -->|gibt Sollbedingungen vor| E"),
                       relations.replace("|Parent|", "|Dataset attachment|", 1),
                       combined.replace("|enthält|", "|Parent|", 1)):
            with self.assertRaises(ValueError):
                concept_svg(broken)
        changed = workflow.replace("Sensorsignal und Referenz vergleichen", "Neue Ergebnisse")
        self.assertIn("Neue Ergebnisse", concept_svg(changed))
        self.assertNotIn("Sensorsignal und Referenz vergleichen", concept_svg(changed))

    def test_existing_notebook_entrypoint_regenerates_companion_and_standalone_svgs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = root / "GaSi_Datenmodell.md"
            concept = root / SOURCE.name
            model.write_bytes((ROOT / "docs/GaSi_Datenmodell.md").read_bytes())
            # Windows checkout must retain the hash of the actual CRLF source.
            original = SOURCE.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            concept.write_bytes(original)
            detailed = generate_html(model)
            self.assertIn('href="GaSi_Konzeptmodell.html"', detailed.read_text(encoding="utf-8"))
            first = concept.with_suffix(".html").read_bytes()
            self.assertIn(sha256(original).hexdigest().encode("ascii"), first)
            for kind in ("workflow", "mapping", "combined", "relations"):
                svg = root / f"GaSi_Konzeptmodell_{kind}.svg"
                self.assertTrue(svg.exists())
                ET.fromstring(svg.read_text(encoding="utf-8"))
            self.assertEqual(concept.read_bytes(), original)
            generate_html(model)
            self.assertEqual(first, concept.with_suffix(".html").read_bytes())
            concept.write_text(original.decode("utf-8").replace("Sensorsignal und Referenz vergleichen", "Neue Ergebnisse"), encoding="utf-8")
            generate_html(model)
            self.assertIn("Neue Ergebnisse", concept.with_suffix(".html").read_text(encoding="utf-8"))

    def test_activity_type_tables_are_visible_and_combined_view_keeps_openbis_levels(self):
        source = SOURCE.read_text(encoding="utf-8")
        html = render_concept_html(source)
        second = re.search(r'<section class="step" id="schritt-2">(.*?)</section>', html, re.S).group(1)
        visible = " ".join(VisibleText(second).text)
        self.assertEqual(visible.count("Entitätstyp"), 3, "One visible type table per GaSi activity")
        for label in ("Vorbereitung: Objekte und Typen", "Messung: Objekte und Typen",
                      "Auswertung: Objekte und Typen", "MFC/MFM", "RAW_DATA", "SOFTWARE_CODE"):
            self.assertIn(label, visible)
        combined = ET.fromstring(concept_svg(graphs(source)[2]))
        text = " ".join(combined.itertext())
        for level in ("SPACE", "PROJECT", "COLLECTION", "OBJECT", "DATASET"):
            self.assertIn(level, text)
        objects = {}
        for node in combined.iter():
            if "data-node" in node.attrib:
                box = next(n for n in node.iter() if n.attrib.get("class") == "node-box")
                objects[node.attrib["data-node"]] = tuple(float(box.attrib[k]) for k in ("x", "y", "width", "height"))
        for activity, output in (("P","DP"),("M","DM"),("E","DE")):
            ax,ay,aw,ah = objects[activity]
            dx,dy,dw,dh = objects[output]
            self.assertEqual(ax+aw/2, dx+dw/2, "Dataset belongs below its generating activity")
            self.assertGreater(dy, max(objects[k][1]+objects[k][3] for k in ("I","P","M","E","Q","G","W","D")))
        self.assertIn('href="GaSi_Konzeptmodell_combined.svg" download', html)

    def test_workflow_shows_sensor_exposure_resources_outputs_and_bam_colors(self):
        graph=graphs(SOURCE.read_text(encoding="utf-8"))[0]
        svg=ET.fromstring(concept_svg(graph))
        expected={"D":("sample","#d5e8d4"),"P":("activity","#fff2cc"),"M":("activity","#fff2cc"),
                  "E":("activity","#fff2cc"),"G":("resource","#e1d5e7"),"I":("resource","#e1d5e7"),
                  "DM":("dataset","#f8cecc"),"C":("conditions","#dae8fc")}
        for key,(role,color) in expected.items():
            node=next(n for n in svg.iter() if n.attrib.get("data-node")==key)
            self.assertEqual(node.attrib["data-role"],role)
            rect=next(n for n in node.iter() if n.attrib.get("class")=="node-box")
            self.assertEqual(rect.attrib["fill"],color)
        self.assertIn("Gas- oder Gasfeuchtesensor"," ".join(svg.itertext()))
        sensor=next(n for n in svg.iter() if n.attrib.get("data-node")=="D")
        self.assertEqual(sensor.attrib.get("data-optional"), "true")
        edges={(n.attrib.get("data-source"),n.attrib.get("data-target")) for n in svg.iter() if "data-source" in n.attrib}
        self.assertIn(("D","M"),edges)
        self.assertFalse(any(end=="D" for start,end in edges),"GaSi does not manufacture another sensor")


if __name__ == "__main__":
    unittest.main()
