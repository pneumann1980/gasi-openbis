# GaSi: aktuelles Setup, Messdaten und openBIS

Das Projekt beschreibt den **aktuellen GaSi-Aufbau** der BAM, FB 8.1. Anlage, Module,
einzelne Geräte und ihre Verwendung bei einer Messung sind getrennt. Es wird keine
Umbauhistorie aufgebaut. Die Geräteunterlagen und alle echten Messdaten bleiben lokal.

## Projekt einrichten, Session und fünf Arbeitsaufgaben

Empfohlene Reihenfolge; jedes Notebook funktioniert unabhängig mit einem frischen Kernel.

| Notebook | Genau eine Aufgabe | Verhalten bei Run All |
|---|---|---|
| [GaSi_Projekt_einrichten.ipynb](GaSi_Projekt_einrichten.ipynb) | Projektpakete im ausgewählten Python-Kernel installieren und prüfen | Installiert `requirements-dev.txt`; kein openBIS-Zugriff |
| [GaSi_00_Session_einrichten.ipynb](GaSi_00_Session_einrichten.ipynb) | Session-Token zentral und verdeckt speichern | Nur lokale `.env`; keine Verbindung zu openBIS |
| [GaSi_01_Datenmodell_HTML_erzeugen.ipynb](GaSi_01_Datenmodell_HTML_erzeugen.ipynb) | Das Modell als verständliche HTML-Grafik erzeugen | Offline; schreibt nur die beiden Modell-HTML-Dateien |
| [GaSi_02_Aktuelles_Setup_pruefen.ipynb](GaSi_02_Aktuelles_Setup_pruefen.ipynb) | Aktuelle Gerätepositionen und Kanalzuordnungen lokal prüfen | Liest die lokale Setup-Datei; erzeugt einen lokalen Bericht |
| [GaSi_03_Messdateien_pruefen.ipynb](GaSi_03_Messdateien_pruefen.ipynb) | CSV-Dateien prüfen und eine lokale Vorschau erzeugen | Offline; Originale unverändert; kein Upload |
| [GaSi_04_Playground_Bestand_lesen.ipynb](GaSi_04_Playground_Bestand_lesen.ipynb) | Sichtbare Bereiche, Typen und Pflichtfelder aus openBIS lesen | Ausschließlich lesend |
| [GaSi_Playground_Ziele_einrichten.ipynb](GaSi_Playground_Ziele_einrichten.ipynb) | Laborbuch- und Inventarziel zentral konfigurieren | Erstellt nur die fehlende lokale JSON-Vorlage; Speichern per Knopf, kein openBIS-Zugriff |
| [GaSi_05_Playground_Schreibtest.ipynb](GaSi_05_Playground_Schreibtest.ipynb) | Einen synthetischen Testlauf schreiben und verifizieren | Vorschau und lesende Prüfung; Schreiben standardmäßig deaktiviert |

Die bisherigen Dateinamen wurden ersetzt:

| Bisher | Jetzt |
|---|---|
| `GaSi_Datenmodell_HTML.ipynb` | Notebook 01 |
| `GaSi_Start.ipynb` | Notebook 03 |
| `GaSi_02_Playground_Check.ipynb` | Notebook 04 |
| `GaSi_03_Playground_Test.ipynb` | Notebook 05 |

Notebook 02 ist neu. Die HTML-Erzeugung befindet sich ausschließlich in Notebook 01;
die Messdateiprüfung hat keinen zusätzlichen HTML-Knopf mehr.
Notebook 00 wird einmal vor den Playground-Schritten beziehungsweise zum Erneuern des
Tokens verwendet. Für die Offline-Schritte 01–03 ist es nicht erforderlich.

## Start in VS Code

Python ab 3.10 sowie die VS-Code-Erweiterungen **Python** und **Jupyter** verwenden.
Falls noch keine Projektumgebung vorhanden ist, einmalig im Repository-Terminal:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install ipykernel
```

Danach **[GaSi_Projekt_einrichten.ipynb](GaSi_Projekt_einrichten.ipynb)** öffnen und oben rechts
**Select Kernel → Python Environments → .venv** wählen. Die Installationszelle verwendet
`sys.executable -m pip install -r requirements-dev.txt` und installiert dadurch sicher
in den ausgewählten Kernel. Die Requirements umfassen pyBIS, HTML-Pakete und Prüfwerkzeuge.
Wenn VS Code zunächst einen fehlenden Kernel meldet, dessen **Install ipykernel**-Aktion verwenden.

Nach der Installation **Restart Kernel** wählen und die abschließende Prüfzelle ausführen.
Sie prüft Paketversionen und echte Imports. Eine Conda-Umgebung mit bestimmtem Namen oder
genau Python 3.14 ist nicht erforderlich; eine passende Conda-Umgebung funktioniert ebenfalls.
Die zuvor im Workshop angezeigte Meldung „Select the pybis Conda environment with Python 3.14“
stammte aus dessen zu enger Umgebungsprüfung. Die Workshop-Einrichtungszellen wurden entsprechend
korrigiert und enthalten jetzt ebenfalls eine aktive Requirements-Installation.

Für reine lokale CSV-/Setup-Prüfung genügt ein Python-Kernel; deren Module benötigen nur
die Standardbibliothek. Alternativ zum Einrichtungsnotebook bleibt die vollständige
Terminal-Installation mit `.\.venv\Scripts\python -m pip install -r requirements-dev.txt` möglich.

Die Arbeitsnotebooks danach öffnen, oben rechts **Select Kernel → Python Environments → .venv** wählen,
**Restart Kernel**, dann **Run All**. Das Arbeitsverzeichnis ist das Repository.
Nach der Umbenennung alte Notebook-Tabs schließen und die neuen Dateien öffnen.
Variablen aus einem vorherigen Notebook werden nicht benötigt.

## Modellgrafik

Quelle: [docs/GaSi_Datenmodell.md](docs/GaSi_Datenmodell.md).
Notebook 01 erzeugt und verlinkt ausdrücklich
[docs/GaSi_Datenmodell_einfach.html](docs/GaSi_Datenmodell_einfach.html).
Die Grafik zeigt Anlage → Module → Geräte sowie den aktuellen Aufbau, Messung und Dateien.
Unter **openBIS-Beziehungen des Schreibtests ansehen** erscheint der konkrete
Erstellungsplan: Collection-Zuordnung, Instrument als Parent des Messlaufs,
Dataset am Messlauf und CSV im Dataset. Er ist von der vorgeschlagenen fachlichen
Ordnung getrennt. Die Grafik behauptet keine bereits angelegten Einträge.
Technische Details bleiben separat in [docs/GaSi_Datenmodell.html](docs/GaSi_Datenmodell.html).

Nach einer Modelländerung Notebook 01 erneut ausführen. Der Generator wird auch beim
erneuten Ausführen nur der Erzeugungszelle frisch geladen. Die HTML-Datei funktioniert
offline und enthält keine privaten Geräteunterlagen oder Messwerte.
Falls HTML-Pakete fehlen, im gewählten Kernel ausführen:

```python
%pip install -r requirements-docs.txt
```

Alternativ: `python gasi_model_html.py` oder unter Windows
`GaSi_Datenmodell_erzeugen.cmd` doppelklicken.

## Aktuelles Setup lokal pflegen

Die tatsächlichen Geräteangaben stehen in **`config/gasi_setup.json`**. Diese Datei ist
von Git ausgeschlossen. In dieser Arbeitskopie wurde ein Entwurf anhand der lokalen
Quellen vorbereitet; bestätigte Unterlagen sind von noch unbestätigten Einbaupositionen
und offenen Geräteangaben getrennt. Es wurden keine echten Geräte registriert.

Fehlt die lokale Datei nach einem frischen Clone, die leere Vorlage kopieren:

```powershell
Copy-Item config/gasi_setup.example.json config/gasi_setup.json
```

Eine vorhandene lokale Datei weiterpflegen. Die Vorlage enthält keine Seriennummern.
Notebook 02 prüft Positionen, eindeutige Gerätekennungen, Bereiche, Gasrollen,
Bezugsbedingungen, Prüfmittelstatus und Kanalzuordnungen. Sein vollständiger Bericht
liegt unter `data/datasheets/_auswertung/GaSi_Aktuelles_Setup.html`.
Die Notebook-Ausgabe zeigt nur eine Zusammenfassung, keine Seriennummern oder Beleginhalte.

Wichtige Felder sind im Notebook beschrieben. `installed_confirmed=true` bedeutet:
dieses konkrete Gerät ist an dieser Position im aktuellen Aufbau bestätigt.
`calibration_status="assessed"` bedeutet: der aktuelle Prüfmittelstatus wurde bewertet;
es bedeutet nicht automatisch „Kalibrierung gültig“. `verified_on` hält die lokale
Prüfung des gesamten aktuellen Standes fest. Belegte Konflikte in `open_issues` bleiben
sichtbar, bis sie geklärt sind. Diese lokale Prüfung bestätigt keine Server-Pflichtfelder.

Bei einem neuen Messlauf soll eine Kopie der tatsächlich verwendeten Setup-Datei
mit Hash zum Lauf gehören. Es werden keine früheren Umbauten nachgepflegt.
Die CSV-Vorschau weist vorhandene Dateien dem aktuellen Stand **nicht automatisch zu**.

## Ablage und Messdateiprüfung

- Geräteunterlagen und lokale Geräteberichte: `data/datasheets/`, von Git ausgeschlossen.
- Setup mit echten Gerätekennungen: `config/gasi_setup.json`, von Git ausgeschlossen.
- Messdaten und lokale Vorschau: `data/measurements/`, von Git ausgeschlossen.
- Fachliteratur und Wiki-Kopie: `data/paper/`, `data/wiki/`.
- Verknüpfung zum ausschließlich lesend verwendeten Betriebscode: `code/`.

Notebook 03 listet CSV-Dateien und prüft das vorhandene 252-Spalten-Loggerformat.
Zu kurze/lange Zeilen sowie ungültige oder nicht endliche Zahlen (`NaN`, `inf`,
Überlauf) in 120 ausgewerteten Zahlenfeldern verhindern die Vorschau.
Leere optionale Werte bleiben von Null unterscheidbar. Eine leere Ablage läuft sauber durch.

Die Vorschau `data/measurements/_local_openbis_import_preview.json` bleibt lokal.
Sie enthält Dateihash und Beispielpunkte; im Notebook werden keine Messpunkte ausgegeben.
Eine Datei ist kein bestätigter Messlauf. Laufkennung, Zeitgrenzen und Gerätebeziehungen
bleiben offen, wenn der Nachweis zur jeweiligen Aufnahme fehlt.

## Playground-Zugang und synthetischer Test

**Zentrale Ablage ist die lokale `.env` im Repository.** Sie ist von Git ausgeschlossen.
Eine leere Datei ist in dieser Arbeitskopie vorbereitet; nach einem Clone kann sie aus
[.env.example](.env.example) kopiert werden. Die Vorlage bleibt ohne Zugangswerte.

Öffne [GaSi_00_Session_einrichten.ipynb](GaSi_00_Session_einrichten.ipynb), wähle den
Projekt-Kernel und führe **Run All** aus. Kopiere den Session-Token im Playground unter
**Tools → User Profile** und füge ihn bei der verdeckten Abfrage ein. Das Notebook
speichert ihn ausschließlich in `.env`; vorhandene andere Sessionwerte bleiben erhalten.
Eine leere Eingabe verändert die Datei nicht.

Notebook 04 und 05 lesen denselben `OPENBIS_PLAYGROUND_TOKEN` automatisch, auch mit
frischem Kernel. Bei fehlendem Zugang geben sie einen Einrichtungshinweis, ohne erneut
nach dem Token zu fragen. Nach Ablauf des Tokens Notebook 00 erneut ausführen und die
Verbindungszelle in 04/05 wiederholen; die Datei wird bei jedem Versuch neu gelesen.

Weitere Session-Credentials können in derselben Datei als `NAME=WERT` stehen.
`gasi_session.session_value("NAME")` liest einen einzelnen benötigten Wert.
Es gibt keine Variablenexpansion oder Ausführung von Dateiinhalten. Werte mit `#`
oder Sonderzeichen bei Bedarf in Anführungszeichen setzen; doppelte Anführungszeichen
verwenden JSON-Escapes. Die Datei enthält Werte im Klartext und bleibt lokal.

Nichtleere Umgebungsvariablen haben Vorrang vor `.env`. Zugangswerte erscheinen weder
in Notebook-Zellen noch in Ausgaben, Ziel-JSON oder HTML-Berichten. pyBIS speichert
keine zusätzliche Token-Datei; Bibliotheksfehler werden ohne Serverdetails ausgegeben.
Kein automatisches Logout entwertet den Token.
Host: ausschließlich `https://playground.datastore.bam.de`, TLS bleibt aktiv.

Notebook 04 liest Bereiche/Projekte/Collections sowie `EXPERIMENTAL_STEP`,
`INSTRUMENT`, `TESTING_EQUIPMENT`, `SETUP.TEST`, `CALIBRATION`, `RAW_DATA`
und `ATTACHMENT` sowie optional `ELN_PREVIEW` einschließlich lesbarer Pflichtfelder und Wertelisten.
Sichtbarkeit, fachliche Eignung und Schreibrechte sind getrennte Fragen.

**Zentrale Zielkonfiguration:** [GaSi_Playground_Ziele_einrichten.ipynb](GaSi_Playground_Ziele_einrichten.ipynb)
nach der Bestandsaufnahme in Notebook 04 öffnen und **Run All** ausführen.
Das Notebook legt die fehlende lokale Vorlage an, übernimmt vorhandene Angaben
und zeigt einen Editor mit genau zwei Collection-Pfaden. **Ziele lokal speichern**
schreibt die gemeinsame Datei `config/playground_test_target.json`.
Notebook 04, Notebook 05 und der Schreibtest lesen stets diese Datei im Repository,
auch bei einem abweichenden Arbeitsverzeichnis. Ihr absoluter Pfad wird ausgegeben.

Die Datei kann alternativ direkt in VS Code bearbeitet werden. Manuelles Kopieren
ist mit dem Einrichtungsnotebook nicht mehr nötig; nach einem Clone bleibt möglich:

```powershell
Copy-Item config/playground_test_target.example.json config/playground_test_target.json
```

`lab_notebook` und `inventory` benötigen exakte bestehende Space-/Project-/Collection-Codes.
`approved_test_scope` dokumentiert die DSSt-Freigabe des FB-8.1-Testbereichs.
Der Editor setzt diesen Status nicht automatisch. Bei bestätigter Freigabe werden
genau die eingetragenen Collections als erlaubte Ziele gespeichert. Sichtbarkeit
und eine lokale Konfiguration ersetzen keine serverseitigen Schreibrechte.
Nur tatsächlich zugewiesene Properties und alle echten Pflichtfelder verwenden.
Die Vorlage behauptet keine BAM-Zielpfade. Stabile Testkennungen beibehalten.
Die Ziel-JSON enthält keine Credentials und ist von Git ausgeschlossen. `.env`
ist ausschließlich die zentrale Session-Ablage; `config/gasi_setup.json` beschreibt
den echten Geräteaufbau. Diese drei Dateien haben unterschiedliche Aufgaben.
Der Editor bietet FB-8.1-Pfadkandidaten aus der letzten Bestandsaufnahme an,
wählt aber keinen automatisch aus. Notebook 04 speichert den vollständigen
lesenden Befund einschließlich großer Wertelisten unter
`.local_playground_test/playground_discovery.json`; diese Datei bleibt ebenfalls lokal.

Nach Prüfung der Vorschau in Notebook 05 die letzte Zelle bewusst aktivieren:
`WRITE_ENABLED = True` und
`WRITE_CONFIRMATION = "WRITE SYNTHETIC TEST TO BAM PLAYGROUND"`.
Dann nur diese Zelle ausführen. Host, Ziele, Typen und Pflichtfelder werden erneut gelesen.

Der Ablauf verwendet genau ein synthetisches Instrument, einen Testmesslauf,
dessen Parent-Beziehung und eine synthetische CSV als Dataset. Er liest die Einträge
zurück, lädt die Datei herunter und vergleicht SHA-256. Wiederholungen und Teilfehler
werden mit denselben Kennungen fortgesetzt. Bei Konflikten wird abgebrochen;
keine automatische Löschung. Nur einen schreibenden Kernel gleichzeitig verwenden.
IDs und Pfade werden nach dem Test angezeigt.

Echte Geräte und Messdaten werden von diesem Test nicht importiert.
Vor Git-Übernahme Notebook-Ausgaben löschen und Schreibschalter/Phrase zurücksetzen.
Alte Session-Parameter wurden aus den bereits versionierten Wiki-Links im aktuellen
Stand entfernt; die Originaldateien bleiben lokal gesichert. Frühere Git-Commits
wurden dabei nicht umgeschrieben.

Der bereitgestellte pyBIS-Workshop wurde ausschließlich lesend abgeglichen.
[Ergebnisse und übernommene Ergänzungen](docs/pybis_Beispielabgleich.md) dokumentieren
API-Begriffe, Namen/Identifier und die Unterscheidung von Dataset-Typen und Dateiformaten.
Das Workshop-Notebook und seine synthetischen Bilddaten werden nicht automatisch ausgeführt
oder hochgeladen; GaSi verwendet weiterhin seine eigene kleine synthetische CSV.

## Prüfung: lokal und live getrennt

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python tests/check_notebooks.py
```

Die lokalen Prüfungen decken CSV-Fehler, aktuelle Setup-Zuordnungen, HTML-Neuerzeugung
und den synthetischen Schreibadapter ab. Jedes Notebook startet im Test mit einem
frischen Kernel; externe Netzwerkzugriffe sind dabei gesperrt.
Der Testclient prüft Wiederholung, Wiederaufnahme nach Teilfehlern und Rückdownload/Hash.
Original-CSVs werden über Hashes auf Unverändertheit geprüft; Ausgaben werden nicht gespeichert.

Prüfstand 12.11.2026: **58 Tests bestanden**, alle acht GaSi-Notebooks mit frischen Kernels
geprüft (insgesamt sechzehn Durchläufe einschließlich Projekt-/Workshop-Einrichtung,
zentraler Session-Einrichtung und Wiederverwendung, leerer Ablage/fehlender Setup-Datei,
zentraler Zieleinrichtung mit Erhalt bestehender Angaben, lesender Testclient-Vorschauen
und aktiviertem synthetischem Schreibtest mit Wiederholung;
Python 3.14.4 / pyBIS 1.37.5). Die pip-Installation wird im Test simuliert; das Ziel ist
der aktuelle Kernel mit dem richtigen Requirements-Pfad. Paketimports werden tatsächlich ausgeführt.
Alle 31 Original-CSVs blieben laut SHA-256 unverändert. Die Grafikprüfung bestätigt
getrennte Boxen und Linien ohne Kreuzungen durch Boxen oder andere Linien.

**Live lesend bestätigt (12.11.2026):** Zugang zum BAM-Playground; FB-8.1-Spaces
und ein Laborbuch-Tutorialprojekt mit drei Collections; das Projekt
`/BAM_EQUIPMENT/8.1_EQUIPMENT_OPEN`, jedoch keine zurückgegebene zugehörige Collection.
`EXPERIMENTAL_STEP`, `INSTRUMENT`, `SETUP.TEST`, `CALIBRATION`, `RAW_DATA`, `ATTACHMENT`
und `ELN_PREVIEW` sind mit Property-Assignments lesbar. `TESTING_EQUIPMENT` ist nicht
im sichtbaren Typkatalog. `INSTRUMENT` benötigt `$NAME`, `MANUFACTURER`, `BAM_OE`
und `BAM_LOCATION_COMPLETE`. Die tatsächlichen Pflichtfelder und offenen
Zuordnungen stehen zusätzlich im [Datenmodell](docs/GaSi_Datenmodell.md).
Beim Live-Abgleich wurde die Wertelistenabfrage auf die bereits geladene pyBIS-Tabelle
umgestellt: der Iterator von `Things` konnte die zweistellige `get_term`-API nicht aufrufen.
Die Organisations-Werteliste enthält den bestätigten Code `OE_8.1`; er wurde in
der lokalen Ziel-JSON ergänzt. `BAM_LOCATION_COMPLETE` ist mit 5.438 Werten lesbar.
Das optionale Vokabular `MEASUREMENT_QUANTITY` blieb unbestätigt.

**Live weiterhin offen:** konkrete freigegebene Test-Collections für Laborbuch und
Inventar (Inventar-Collection nicht sichtbar oder noch nicht vorhanden), DSSt-Freigabe,
Standortcode des synthetischen Instruments, vorhandene Geräteeinträge sowie Schreibrechte
und Server-Validatoren. Die zentrale Ziel-JSON ist lokal vorbereitet, bleibt ohne
bestätigte Ziele und Freigabe gesperrt. Der echte synthetische Upload mit Rückdownload
wurde bewusst noch nicht ausgeführt; der manuelle Schreibschalter bleibt deaktiviert.
Konkrete offene Fragen zum aktuellen Aufbau stehen im lokalen Setup-Bericht;
die frühere ausführliche Bestandsaufnahme dient nur noch als Quellenablage.

Referenzen: [BAM Laborbuch](https://bamresearch.github.io/openBIS-data-store-tutorials/lab-notebook/),
[Inventar](https://bamresearch.github.io/openBIS-data-store-tutorials/inventory-data-stewards/),
[Objektverweise](https://bamresearch.github.io/bam-masterdata/howtos/object_references/),
[pyBIS](https://openbis.readthedocs.io/en/20.10.12-plus/software-developer-documentation/apis/python-v3-api.html).
