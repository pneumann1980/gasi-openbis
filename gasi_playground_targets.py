"""Central local target editor. No connection or openBIS mutation on import/click."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

import gasi_openbis_playground as playground


def initialize_target_config(path=None):
    """Create the local template once; never replace an existing local file."""
    path = Path(path) if path is not None else playground.TARGET_CONFIG_PATH
    if not path.exists():
        template = playground.TARGET_TEMPLATE_PATH.read_text(encoding="utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(template)
        except FileExistsError:
            pass
    return playground.load_target_config(path)


def collection_codes(path):
    parts = path.strip().split("/")
    if len(parts) != 4 or parts[0] != "":
        raise playground.CheckFailed("Collection als /SPACE/PROJECT/COLLECTION eingeben; vorhandene openBIS-Codes verwenden.")
    group = dict(zip(("space", "project", "collection"), parts[1:]))
    playground.target_path(group)
    return group


def save_target_config(config, path=None):
    """Persist explicit targets atomically; this never grants server permissions."""
    path = Path(path) if path is not None else playground.TARGET_CONFIG_PATH
    if not isinstance(config, dict):
        raise playground.CheckFailed("Zielkonfiguration muss ein JSON-Objekt sein.")
    for key in ("lab_notebook", "inventory"):
        playground.target_path(config.get(key, {}))
    text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                         prefix=".playground-target-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def show_target_editor(path=None):
    """An explicit save button edits the one shared JSON, never the remote server."""
    import ipywidgets as widgets
    from IPython.display import display

    path = Path(path) if path is not None else playground.TARGET_CONFIG_PATH
    config, message = initialize_target_config(path)
    print(message)
    if config is None:
        print("Bestehende Datei korrigieren; sie wird nicht überschrieben.")
        return None
    def current_path(key):
        try:
            return playground.target_path(config.get(key, {}))
        except playground.CheckFailed:
            return ""
    layout = widgets.Layout(width="100%")
    style = {"description_width": "160px"}
    choices = {"lab_notebook": [], "inventory": []}
    try:
        report = json.loads(playground.DISCOVERY_REPORT_PATH.read_text(encoding="utf-8"))
        if report.get("host") == playground.PLAYGROUND_HOST:
            for collection in report.get("collections", []):
                if collection.get("fb81_candidate"):
                    collection_path = collection["path"]
                    if any(word in collection_path for word in ("EQUIPMENT", "INVENTORY")):
                        choices["inventory"].append(collection_path)
                    elif not any(word in collection_path for word in ("ELN_SETTINGS", "PUBLICATIONS", "MATERIALS", "METHODS", "STORAGE")):
                        choices["lab_notebook"].append(collection_path)
            print("Pfadvorschläge stammen aus dem letzten lokalen Lesebefund; explizite Zielwahl erforderlich.")
            if not choices["inventory"]:
                print("Keine FB-8.1-Inventar-Collection im letzten Befund. Exakten Zielpfad bzw. Leserechte mit DSSt klären.")
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        pass
    lab = widgets.Combobox(value=current_path("lab_notebook"), options=choices["lab_notebook"],
        description="Laborbuch-Collection", layout=layout, style=style, ensure_option=False)
    inventory = widgets.Combobox(value=current_path("inventory"), options=choices["inventory"],
        description="Inventar-Collection", layout=layout, style=style, ensure_option=False)
    properties = widgets.Textarea(value=json.dumps({k: config.get(k) for k in (
        "instrument", "run_properties", "dataset_properties")}, ensure_ascii=False, indent=2),
        layout=widgets.Layout(width="100%", height="300px"))
    advanced = widgets.Accordion(children=[properties], titles=("Typ und Pflichtfelder aus Notebook 04 ergänzen",))
    advanced.selected_index = None
    button = widgets.Button(description="Ziele lokal speichern", button_style="primary", layout=widgets.Layout(width="210px"))
    output = widgets.Output()
    def save(_):
        with output:
            output.clear_output()
            try:
                # Reload first: preserve unrelated changes made in the JSON meanwhile.
                updated, _ = playground.load_target_config(path)
                if updated is None:
                    raise playground.CheckFailed("Zentrale Datei nicht lesbar; zuerst JSON korrigieren.")
                updated = deepcopy(updated)
                updated["lab_notebook"] = collection_codes(lab.value)
                updated["inventory"] = collection_codes(inventory.value)
                fields = json.loads(properties.value)
                if not isinstance(fields, dict) or set(fields) != {"instrument", "run_properties", "dataset_properties"}:
                    raise playground.CheckFailed("Erweiterte Angaben müssen instrument, run_properties und dataset_properties enthalten.")
                updated.update(fields)
                updated["test_scope"] = dict(
                    lab_notebook_path_prefix=playground.target_path(updated["lab_notebook"]),
                    inventory_path_prefix=playground.target_path(updated["inventory"]))
                saved = save_target_config(updated, path)
                print(f"Gespeichert: {saved.as_posix()}. Einrichtung erneut ausführen; keine openBIS-Einträge angelegt.")
            except playground.CheckFailed as exc:
                print(str(exc))
            except (ValueError, TypeError, AttributeError, OSError):
                print("Nicht gespeichert. Pfade, JSON-Struktur und lokalen Dateizugriff prüfen.")
    button.on_click(save)
    editor = widgets.VBox([lab, inventory, advanced, button, output])
    display(editor)
    return editor
