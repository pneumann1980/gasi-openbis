# GaSi: aktuelles Setup, Messdaten und openBIS

Das Projekt beschreibt den **aktuellen GaSi-Aufbau** der BAM, FB 8.1. Anlage, Module,
einzelne Geräte und ihre Verwendung bei einer Messung sind getrennt. Es wird keine
Umbauhistorie aufgebaut. Die Geräteunterlagen und alle echten Messdaten bleiben lokal.

## Kürzester Weg zum ersten Erfolg

Projektumgebung und GaSi-Zielbereiche sind in dieser Arbeitskopie bereits eingerichtet.
Die Notebooks jeweils mit dem Projekt-Kernel und **Restart Kernel → Run All** starten:

1. **`GaSi_00_Session_einrichten.ipynb`** – Session-Token eintragen oder erneuern.
   Bei bereits gespeichertem gültigem Token kann dieser Schritt entfallen.
2. **`GaSi_06_Geraetezuordnung_pruefen.ipynb`** – lokalen Gerätebericht öffnen.
   Erwartung: 17 Positionen, zehn belegte Identitäten, sieben offene Identitäten.
   Bereits gespeicherte openBIS-IDs und Browserlinks stehen im Bericht.
3. **`GaSi_07_Geraeteinventar_anlegen.ipynb`** – Bestand lesen und Vorschau prüfen.
   Nach erfolgreicher Erstregistrierung zeigt `reuse: 10` die zehn vorhandenen Geräte.
   Der Link zum lokalen HTML-Bericht führt zu ihren Browserlinks.

**Das ist der erste sichtbare Erfolg:** Die zehn belegten Geräte sind in der Collection
`/8.1_EQUIPMENT/GASI/INSTRUMENTS` wiederzufinden. Für einen bewussten erneuten
Schreibnachweis in Notebook 07 die letzte Zelle mit `REGISTER_ENABLED = True` und
der dort angegebenen Bestätigungsphrase ausführen. Erwartung bei Wiederholung:
**0 neu angelegt, 10 wiederverwendet**.

Für den vollständigen technischen Uploadtest danach optional
**`GaSi_05_Playground_Schreibtest.ipynb`** öffnen. Run All bleibt eine Vorschau;
die bewusst aktivierte Schreibzelle verwendet einen separaten synthetischen
Testmesslauf mit Testinstrument und CSV und bestätigt den Rückdownload per SHA-256.
Die Einrichtungsnotebooks für Projekt und Testbereiche sind nur bei einer neuen
Arbeitskopie bzw. fehlender Einrichtung nötig. Notebook 04 dient der ausführlichen
Bestandsdiagnose, 01 der Modellgrafik, 02 der Setup-Prüfung und 03 den lokalen Messdateien.

## Projekt einrichten, Session und Arbeitsnotebooks

Empfohlene Reihenfolge; jedes Notebook funktioniert unabhängig mit einem frischen Kernel.

| Notebook | Genau eine Aufgabe | Verhalten bei Run All |
|---|---|---|
| [GaSi_Projekt_einrichten.ipynb](GaSi_Projekt_einrichten.ipynb) | Projektpakete im ausgewählten Python-Kernel installieren und prüfen | Installiert `requirements-dev.txt`; kein openBIS-Zugriff |
| [GaSi_00_Session_einrichten.ipynb](GaSi_00_Session_einrichten.ipynb) | Session-Token zentral und verdeckt speichern | Nur lokale `.env`; keine Verbindung zu openBIS |
| [GaSi_01_Datenmodell_HTML_erzeugen.ipynb](GaSi_01_Datenmodell_HTML_erzeugen.ipynb) | Modellübersicht und die vier BAM-Konzeptschritte erzeugen | Offline; schreibt Modell-/Konzept-HTML und drei Konzept-SVGs |
| [GaSi_02_Aktuelles_Setup_pruefen.ipynb](GaSi_02_Aktuelles_Setup_pruefen.ipynb) | Aktuelle Gerätepositionen und Kanalzuordnungen lokal prüfen | Liest die lokale Setup-Datei; erzeugt einen lokalen Bericht |
| [GaSi_03_Messdateien_pruefen.ipynb](GaSi_03_Messdateien_pruefen.ipynb) | CSV-Dateien prüfen und eine lokale Vorschau erzeugen | Offline; Originale unverändert; kein Upload |
| [GaSi_04_Playground_Bestand_lesen.ipynb](GaSi_04_Playground_Bestand_lesen.ipynb) | Sichtbare Bereiche, Typen und Pflichtfelder aus openBIS lesen | Ausschließlich lesend |
| [GaSi_Playground_Testbereich_anlegen.ipynb](GaSi_Playground_Testbereich_anlegen.ipynb) | Die fehlenden GaSi-Testprojekte und Collections einmalig einrichten | Vorschau; Anlage erst nach bewusster Aktivierung |
| [GaSi_Playground_Ziele_einrichten.ipynb](GaSi_Playground_Ziele_einrichten.ipynb) | Laborbuch- und Inventarziel zentral konfigurieren | Erstellt nur die fehlende lokale JSON-Vorlage; Speichern per Knopf, kein openBIS-Zugriff |
| [GaSi_05_Playground_Schreibtest.ipynb](GaSi_05_Playground_Schreibtest.ipynb) | Einen synthetischen Testlauf schreiben und verifizieren | Vorschau und lesende Prüfung; Schreiben standardmäßig deaktiviert |
| [GaSi_06_Geraetezuordnung_pruefen.ipynb](GaSi_06_Geraetezuordnung_pruefen.ipynb) | Gerätebelege und Anlagen-Inventarnummern lokal abgleichen | Offline; erzeugt ausschließlich lokale Berichte |
| [GaSi_07_Geraeteinventar_anlegen.ipynb](GaSi_07_Geraeteinventar_anlegen.ipynb) | Belegte Geräteidentitäten im eigenen GaSi-Inventar registrieren | Vorschau und lesender Dublettenabgleich; Schreiben deaktiviert |

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

**Neu: [GaSi-Konzeptmodell in vier Schritten](docs/GaSi_Konzeptmodell.html)**:
Forschungsablauf zeichnen, Entitäten und Typen bestimmen, in Laborbuch/Inventar
einordnen und Objekte verbinden. Die HTML zeigt einen Schritt pro Ansicht;
Tabellen und Fachfragen lassen sich bei Bedarf aufklappen. Die
[Markdown-Quelle](docs/GaSi_Konzeptmodell.md) enthält die Entscheidungen und Fundstellen.

**Neu erzeugen:** Notebook **01** mit frischem Kernel öffnen und **Run All**
ausführen. Den erzeugten Link **Einfache Grafik öffnen** anklicken und dort
**Forschungsablauf: die vier BAM-Schritte ansehen** wählen. Derselbe Aufruf
aktualisiert die neue Konzeptansicht und die drei separat nutzbaren SVGs
`GaSi_Konzeptmodell_workflow.svg`, `_mapping.svg` und `_relations.svg` in `docs/`.
Kein zusätzliches Notebook und kein BAM-Zugang erforderlich.

Quelle: [docs/GaSi_Datenmodell.md](docs/GaSi_Datenmodell.md).
Notebook 01 erzeugt und verlinkt ausdrücklich
[docs/GaSi_Datenmodell_einfach.html](docs/GaSi_Datenmodell_einfach.html).
Die Grafik zeigt Anlage → Module → Geräte sowie den aktuellen Aufbau, Messung und Dateien.
Unter **openBIS-Beziehungen des Schreibtests ansehen** erscheint der konkrete
Erstellungsplan: Collection-Zuordnung, Instrument als Parent des Messlaufs,
Dataset am Messlauf und CSV im Dataset. Er ist von der vorgeschlagenen fachlichen
Ordnung getrennt. Die Grafik behauptet keine bereits angelegten Einträge.
Technische Details bleiben separat in [docs/GaSi_Datenmodell.html](docs/GaSi_Datenmodell.html).

Der Konzeptabgleich vom 13.11.2026 folgt der
[aktuellen BAM-Anleitung](https://datastore.bam.de/en/openbis_20-10-12/how-to_guides/user_ui/represent_research_data)
und dem [EuVSOP-Beispiel](https://datastore.bam.de/en/use_cases/euvsop).
Das Zielmodell trennt **Vorbereitung → Messung → Auswertung**. Forschungsdateien
gehören an ihre erzeugende Tätigkeit; Auswerteergebnisse damit an die Auswertung.
Die Geräteübersicht zeigt ergänzend nur Aufbau und Messung.
Eigene Anlagen-/Modulobjekte sind zunächst nicht erforderlich; ein Prüfling
ist eine Rolle und bekommt keinen zweiten Eintrag neben seiner Geräteidentität.
Die [Parserübersicht](https://datastore.bam.de/en/parsers) dient als Ausgangspunkt
für einen späteren GaSi-Importer, sobald Laufgrenzen und Kanalzuordnungen feststehen.

Dieser Schritt ändert die **lokale Modelldokumentation und ihre Visualisierung**.
Die drei Forschungsaktivitäten, echte Laborbuch-Collections sowie Gas-/SOP- und
Softwareobjekte wurden damit noch nicht live angelegt. Das vorhandene Geräteinventar
und der synthetische Test bleiben die separat bestätigten Instanzbefunde.

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

## Geräteidentitäten und Inventarnummern zusammenführen

Notebook 06 liest das aktuelle Setup, die referenzierten Gerätebelege und die lokale
`*Inventar.csv`. Bei mehreren Inventarquellen wird `inventory_source` in der ignorierten
`config/gasi_setup.json` ausdrücklich gesetzt. Es werden ausschließlich die Geräte des
aktuellen Setup-Entwurfs geprüft, keine vollständigen Anlagenlisten oder Altbestände importiert.

Der lokale Bericht `data/datasheets/_auswertung/GaSi_Geraetezuordnung.html` zeigt pro
Position Hersteller, Modell, Seriennummer, Beleg, Inventarkandidaten und offene Angaben.
Ein Modell- oder Bereichstreffer weist eine Anlagen-Inventarnummer noch keinem
bestimmten Gerät zu. Bestätigte Zuordnungen werden separat als `inventory_assignment`
mit `confirmed`, vollständiger `number` und `evidence` geführt. Die Originalnummer bleibt
als Text erhalten. Für openBIS werden Haupt- und Unternummer gegebenenfalls in die
Integer-Properties `INVENTORY_NO` und `INVENTORY_NO_ADD` aufgeteilt; führende Nullen
bleiben in der lokalen Referenz und den Metadaten-Notizen erhalten. Unbestätigte Nummern
werden nicht in diese Properties übernommen. Preise werden nicht übernommen.

Notebook 07 prüft die belegten Identitäten gegen sichtbare `INSTRUMENT`-Einträge.
Hersteller und Seriennummer identifizieren das Gerät unabhängig von Position und
Modellkorrekturen. Eindeutige Bestände werden wiederverwendet; abweichende Modelle,
mehrdeutige Seriennummern oder unlesbare gespeicherte Verweise bleiben gesperrt.
Eine dokumentierte Identität benötigt noch keine bestätigte Einbauposition oder
Kalibriergültigkeit. Diese Statuswerte werden durch die Registrierung nicht verändert.

**Das zentrale Ziel steht in derselben lokalen Ziel-JSON** unter `gasi_inventory`:

```json
{
  "target": {"space": "8.1_EQUIPMENT", "project": "GASI", "collection": "INSTRUMENTS"},
  "location": {"code": "", "confirmed": false, "evidence": ""},
  "authorization": {"kind": "user_instruction", "reference": ""}
}
```

`authorization.reference` dokumentiert den Arbeitsauftrag und behauptet keine formelle
BAM-Freigabe. `location` benötigt den **tatsächlichen** Standort, einen gültigen
`BAM_LOCATION_COMPLETE`-Code und einen Beleg. Angaben aus Postanschriften oder
Wareneingangshinweisen werden nicht als Gerätestandort verwendet. Die synthetische
Testkonfiguration liefert keinen Ersatzwert. Die beiden Zielabschnitte bleiben beim
Speichern jeweils erhalten.

Nach Prüfung des Berichts in Notebook 07 `REGISTER_ENABLED = True` und
`REGISTER_CONFIRMATION = "REGISTER DOCUMENTED GASI DEVICE IDENTITIES ON PLAYGROUND"`
setzen und ausschließlich diese Zelle ausführen. Host, Ziel, Belege, Hashes, Typen,
Pflichtfelder und Wertelisten werden erneut geprüft. Es werden nur Gerätemetadaten
geschrieben; keine Messdaten oder Originalbelege hochgeladen. Neue Einträge werden
zurückgelesen, ihre IDs in `openbis_identifier`/`openbis_perm_id` der lokalen Setup-Datei
gespeichert. Teilfehler und Wiederholungen verwenden dieselbe Geräteidentität.

Lokaler Stand: 17 Positionen, zehn belegte Hersteller-/Modell-/Seriennummernidentitäten,
keine bestätigten Anlagen-Inventarnummern. Sieben Identitäten benötigen weitere Belege.
**Live-Prüfung:** Der eigene Bereich `/8.1_EQUIPMENT/GASI/INSTRUMENTS` ist angelegt.
Die zehn belegten Identitäten sind am bestätigten Standort registriert und
zurückgelesen; sieben unvollständige Identitäten bleiben offen. Unbestätigte
Anlagen-Inventarnummern, Einbaupositionen und Kalibrierstatus werden nicht als
bestätigt übernommen. Die genaue Standortangabe bleibt in der privaten Ziel-JSON.
Falls die BAM-Werteliste nur einen übergeordneten Raum enthält, bleiben der
vollständige gemeldete Raumzusatz und die Zuordnungsgenauigkeit zusätzlich in
`NOTES.location` und im lokalen HTML-Bericht erhalten.
Die erneute Live-Registrierung bestätigte **0 neue und 10 wiederverwendete Geräte**.
Alle zehn Einträge wurden anschließend einzeln auf Identität, Standortdetails und
fehlende Beleg-/Messdatei-Datasets kontrolliert. Lokale Einbau- und Kalibrierstatus
blieben unverändert; offene Anlagen-Inventarnummern wurden nicht eingetragen.

## Fachlich nächster Schritt

Die Geräteidentitäten stehen nun bereit. Als Nächstes wird der **tatsächlich
verwendete Aufbau** bestätigt: welches Gerät an welcher Position arbeitet,
welche Kanäle und Messorte dazugehören und welche offenen Bereichs-/Skalierungsfragen
noch relevant sind. Dafür dienen der lokale Bericht und Notebook 02. Die Registrierung
setzt `installed_confirmed` oder den Kalibrierstatus nicht automatisch auf bestätigt.

Danach kann ein erster GaSi-Messlauf die tatsächlich beteiligten Geräte als Parents
referenzieren und die verwendete Setup-Datei als Snapshot mit Hash erhalten.
Die noch offenen Geräteidentitäten und Anlagen-Inventarnummern werden gezielt
ergänzt; Originalmessdaten bleiben bis zu einem gesondert geprüften Import lokal.

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
`approved_test_scope` dokumentiert den lokalen Auftrag bzw. Freigabevermerk für den synthetischen Testbereich.
Die historische Bezeichnung `steward_approved` ersetzt keine formelle BAM-Freigabe
und keine serverseitige Rolle. Der hier verwendete Vermerk bezieht sich auf den
ausdrücklichen Nutzerauftrag in dieser Sitzung.
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

Fehlen die Test-Collections in einer neuen Instanz, übernimmt
[GaSi_Playground_Testbereich_anlegen.ipynb](GaSi_Playground_Testbereich_anlegen.ipynb)
die einmalige Anlage: Projekt `GASI_TEST` im eigenen FB-8.1-Laborbuch und in
`8.1_EQUIPMENT`, darin `RUNS` bzw. `INSTRUMENTS`. Der Ablauf liest vorhandene
Testmarker zurück und vervollständigt Teilstände ohne Dubletten. Er ändert keine
Rollen, globalen Typen oder Wertelisten. Nach erfolgreicher Rückprüfung wird die
zentrale Ziel-JSON gespeichert. Danach sind 04 und 05 die normalen Arbeitsschritte;
die Ziele müssen nicht erneut manuell eingerichtet werden.

Für das fiktive Instrument ist ein gültiger Standortcode technisch erforderlich.
Die Session darf die globale Standort-Werteliste nicht ergänzen. Deshalb wird ein
bestehender Wert ausschließlich als synthetischer Pflichtfeld-Testwert verwendet:
`synthetic_location.not_a_physical_assignment=true` und die Beschreibung am Instrument
kennzeichnen ausdrücklich, dass dies **keine Raumzuordnung** ist. Für echte Geräte
muss der belegte tatsächliche Standort verwendet werden.

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

**Konzeptabgleich 13.11.2026:** 89 lokale Tests bestanden. Notebook 01 wurde
zusätzlich mit frischem Kernel und gesperrtem Netzwerk ausgeführt: beide
Markdown-Quellen unverändert, alle drei HTML-Dateien und die drei Konzept-SVGs
erzeugt. Die vier Ansichten wurden in Edge geprüft; je Auswahl ist genau ein
Schritt sichtbar. Alle neuen Diagrammkanten und Beschriftungen stammen aus der
Konzeptquelle; Boxen und Verbindungslinien überschneiden sich in den geprüften
Layouts nicht. Die verlinkten BAM-Seiten wurden gelesen. Es fand für diesen
Konzeptabgleich kein neuer Live-Schreibtest statt.

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
.\.venv\Scripts\python tests/check_notebooks.py
```

Die lokalen Prüfungen decken CSV-Fehler, aktuelle Setup-Zuordnungen, HTML-Neuerzeugung
und den synthetischen Schreibadapter ab. Jedes Notebook startet im Test mit einem
frischen Kernel; externe Netzwerkzugriffe sind dabei gesperrt.
Der Testclient prüft Wiederholung, Wiederaufnahme nach Teilfehlern und Rückdownload/Hash.
Original-CSVs werden über Hashes auf Unverändertheit geprüft; Ausgaben werden nicht gespeichert.

Prüfstand 12.11.2026: **85 Tests bestanden**, alle elf GaSi-Notebooks mit frischen Kernels
geprüft (insgesamt vierundzwanzig lokale Durchläufe einschließlich Projekt-/Workshop-Einrichtung,
zentraler Session-Einrichtung und Wiederverwendung, leerer Ablage/fehlender Setup-Datei,
zentraler Zieleinrichtung mit Erhalt bestehender Angaben, lesender Testclient-Vorschauen
aktivierter Einrichtung mit Wiederholung, aktiviertem synthetischem Schreibtest mit Wiederholung,
lokaler Gerätezuordnung und isolierter Geräte-Registrierung mit Wiederholung;
Python 3.14.4 / pyBIS 1.37.5). Die pip-Installation wird im Test simuliert; das Ziel ist
der aktuelle Kernel mit dem richtigen Requirements-Pfad. Paketimports werden tatsächlich ausgeführt.
Alle 31 Original-CSVs blieben laut SHA-256 unverändert. Die Grafikprüfung bestätigt
getrennte Boxen und Linien ohne Kreuzungen durch Boxen oder andere Linien.
Zusätzlich blieben die fünf verwendeten Gerätebelege und die Inventar-CSV laut ihren
vorhandenen Hashes unverändert. Die Geräte-Prüfungen decken mehrdeutige Inventarnummern,
führende Nullen, Belegseiten und Dateihashes, unveränderte Einbau-/Prüfmittelstatus,
Dubletten, Wiederaufnahme nach gespeichertem Teilstand und die Sperre bei fehlendem
tatsächlichem Standort ab. Synthetische und echte Zielabschnitte überschreiben einander nicht.
Zusätzlich wurden 06 und 07 mit frischen Kernels und den tatsächlichen lokalen Daten
ausgeführt: 06 mit gesperrtem Netzwerk, 07 gegen den Playground mit gesperrten
Anlagefunktionen. Der erste Erfolgsweg zeigt zehn gespeicherte Browserlinks bzw.
zehn vorhandene Geräte. Der separate synthetische Schreibtest wurde anschließend
ebenfalls live wiederholt: dieselben drei IDs, bestätigter Parent und identischer
CSV-Hash nach Rückdownload.

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

**Live schreibend bestätigt:** Die Test-Collections
`/8.1_PNEUMANN/GASI_TEST/RUNS` und `/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS` wurden
auf ausdrücklichen Nutzerauftrag angelegt und zurückgelesen. Die zentrale Ziel-JSON
enthält die beiden Pfade, den auf sie begrenzten Freigabevermerk und den als
synthetischen Pflichtfeld-Testwert gekennzeichneten Standortcode.
Genau ein Instrument, ein Messlauf, dessen Parent-Beziehung und ein RAW_DATA-Dataset
wurden live geprüft. Auch die Wiederaufnahme nach absichtlichem Abbruch hinter dem
Instrument-Speichern und ein zweiter vollständiger Start sind bestätigt: gleiche IDs,
keine Dubletten, beide CSV-Rückdownloads mit identischem SHA-256.
[IDs, Browserlinks und vollständiger Testnachweis](docs/GaSi_Playground_Testnachweis.md).
Die Notebook-Schreibschalter bleiben für Run All deaktiviert.
Auch die erneute Einrichtung wurde live bestätigt: `created=[]`. Dabei wurde die
pyBIS-Objektiteration von Katalogen und Property-Assignments durch das Lesen ihrer
bereits geladenen Tabellen ersetzt; dadurch entfallen unnötige Einzelabfragen
und der belegte Deepcopy-Fehler bei bestehenden Collections.

**Für echte Geräte weiterhin fachlich zu bestätigen:** tatsächliche Raumzuordnung,
Geräteidentität, aktueller Einbau, Prüfmittelstatus und vorhandene Inventareinträge.
Die globale Standort-Werteliste darf mit dieser Session nicht verändert werden;
der Test verwendet ausschließlich gekennzeichnete synthetische Pflichtfeldwerte.
Konkrete offene Fragen zum aktuellen Aufbau stehen im lokalen Setup-Bericht;
die frühere ausführliche Bestandsaufnahme dient nur noch als Quellenablage.

Referenzen: [BAM Laborbuch](https://bamresearch.github.io/openBIS-data-store-tutorials/lab-notebook/),
[Inventar](https://bamresearch.github.io/openBIS-data-store-tutorials/inventory-data-stewards/),
[Objektverweise](https://bamresearch.github.io/bam-masterdata/howtos/object_references/),
[pyBIS](https://openbis.readthedocs.io/en/20.10.12-plus/software-developer-documentation/apis/python-v3-api.html).
