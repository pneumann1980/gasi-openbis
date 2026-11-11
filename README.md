# GaSi-Labor: Dateisichtung

## Start in VS Code

Repository in VS Code öffnen und `GaSi_Start.ipynb` starten. Im Notebook **Run All** ausführen. Es benötigt nur die Python-Standardbibliothek.

## Ablage

- Geräteunterlagen (z. B. Datenblätter und Handbücher): `data/datasheets/`
- Messdaten: `data/measurements/`
- Fachliteratur: `data/paper/`
- Software-Dokumentation: `data/wiki/`
- Code und Verknüpfungen: `code/`

Das Notebook listet die Dateien in diesen Ordnern und weist auf leere Ablagen hin.

## Datenmodell und lokale Vorschau

Das fachliche Modell und die vorgeschlagene BAM-Data-Store-Zuordnung stehen in [docs/GaSi_Datenmodell.md](docs/GaSi_Datenmodell.md). `GaSi_Start.ipynb` liest und validiert die vorhandenen CSV-Testläufe lokal und schreibt eine Beispielvorschau nach `data/measurements/_local_openbis_import_preview.json`. Die Datei wird durch `.gitignore` ausgeschlossen. Das Notebook verbindet sich nicht mit openBIS und registriert keine Daten.
