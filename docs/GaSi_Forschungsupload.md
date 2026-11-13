# GaSi: vom Sensor-Prüfling zum überprüften Forschungsupload

## Fachliche Festlegung

Unser Prüfobjekt („Sample“) ist **ein vorhandener Gas- oder Gasfeuchtesensor**.
Es wird durch GaSi weder hergestellt noch durch einen Messlauf vervielfältigt.
Falls das Gerät bereits im Inventar existiert, bleibt seine Identität erhalten.
Das fachliche Wort Sample schreibt den openBIS-Typ `SAMPLE` nicht vor.

Die Farblogik der vom Nutzer bereitgestellten `20260630_1_workflow.svg` wird in der
[GaSi-Ablaufgrafik](GaSi_Konzeptmodell.html) verwendet:

| Farbe | GaSi-Bedeutung |
|---|---|
| Gelb | Vorbereitung, Beaufschlagung/Messung und Auswertung |
| Grün | Der Sensor als Prüfobjekt; vorhandene Identität |
| Lila | Verwendete Gasquellen, GaSi-Geräte, Referenzen, Verfahren und Software |
| Rot | Dateien/Datasets der jeweils erzeugenden Tätigkeit |
| Blau | Belastungsprofil als Parameterkontext, kein zusätzliches Sensor-/Gasflaschenobjekt |

„Treatment Solution“ der Vorlage wird für GaSi durch **Gasquellen und ein
Belastungsprofil** ersetzt. Temperatur und Feuchte sind Bedingungen. Sie sind
keine Chemikalien und keine eigene Sensorprobe. Beaufschlagung und
Signalerfassung bilden gemeinsam den Messlauf, da der Sensor gerade unter diesen
Bedingungen beobachtet wird. Ein eigener Konditionierungsschritt braucht einen
realen, gesondert dokumentierten Vorgang; er wird nicht aus der Vorlage erfunden.

## Was vor dem ersten echten Upload bekannt sein muss

| Information | Was noch konkret fehlt / zu bestätigen ist |
|---|---|
| Sensor | Identität des tatsächlich getesteten Gas-/Gasfeuchtesensors; vorhandene openBIS-ID oder Angaben für seine einmalige Registrierung. Kein konkreter DUT ist aus den bereitgestellten Loggerdateien zweifelsfrei zugeordnet. |
| Sensor-Objekttyp | Vorhandenes `INSTRUMENT` verwenden, wenn es ein so verwaltetes Gerät ist. Für einen neuen Prüfling `TEST_OBJECT` oder passenden `SAMPLE`-Typ samt Pflichtfeldern in Notebook 04 prüfen. Nicht beide für denselben Sensor anlegen. |
| Gasquellen | Tatsächlich eingesetzte Flaschen/Chargen, Trägergas, Komponenten, nomineller Gehalt und trocken/feucht-Bezug; vorhandene Materialobjekte und gegebenenfalls Zertifikate. Ein Rezept-Gascode allein identifiziert keine Flasche. |
| Temperatur | Was wird geregelt, was nur gemessen? Kammer, Gas am Prüfling und Sensorkörper unterscheiden. Werte, Einheiten, Messorte und Kanalbezug bestätigen. `KLIKA_C` ist nicht automatisch Sensortemperatur. |
| Feuchte | Relative Feuchte, Taupunkt, Frostpunkt oder Stoffmengenanteil von Wasser; Einheit, Wasser-/Eisbezug und Messort. Bei relativer Feuchte zugehörigen Temperaturbezug nennen. Fehlend ist nicht „trocken“. |
| Referenz und Sensorantwort | Kanäle, physische Objekte, Größen, Einheiten und Messorte bestätigen. A5B-Spannungen werden nicht automatisch als Sensorsignal eingestuft. Die Eignung/Gültigkeit der Referenz ist fachlich zu bewerten. |
| Lauf und Stufen | Fachliche Laufgrenzen, Zeitstempel mit UTC-Offset und bestätigte Datensatzbereiche pro Datei und Messstufe. Eine Datei ist nicht automatisch ein Lauf. |
| Ziele | Drei ausdrückliche Collection-Ziele im freigegebenen FB-8.1-Laborbuchprojekt; diese Ziele werden nicht aus dem persönlichen synthetischen Test abgeleitet. |
| Instanzprüfung | Erneuerter Session-Zugang und lesender Schema-/Ressourcenabgleich. Der zusätzliche Zugriff am 13.11.2026 war nicht erfolgreich; keine neuen Typ- oder Schreibrechtsbestätigungen daraus ableiten. |

Der vorhandene Gerätebestand dokumentiert zehn Identitäten des Prüfstands.
Das bestätigt noch nicht den Einbau aller Komponenten, den konkreten Sensor oder
eine laufbezogen gültige Referenz. Seriennummern und konkrete Gerätebelege bleiben
in den lokalen Berichten.

## Lokale Konfiguration

`GaSi_08_Forschungsablauf_hochladen.ipynb` legt eine fehlende
`config/gasi_run.json` einmal aus [der leeren Vorlage](../config/gasi_run.example.json)
an. Vorhandene Angaben werden erhalten. Die Datei bleibt außerhalb von Git.

| Abschnitt | Inhalt |
|---|---|
| `run_id` | Stabile fachliche Kennung des Messlaufs |
| `analysis_id` | Eigene Kennung der Auswertung; neue Auswertung erhält eine neue Kennung |
| `dut` | Vorhandene Objekt-ID, `gas_sensor` oder `gas_humidity_sensor`, bestätigte Identität |
| `resources` | Vorhandene Geräte-/Referenz- und Gasquellen-IDs; gegebenenfalls SOP-/Softwareobjekte |
| `software_versions` | Getrennte Versionen von Erfassung und Auswertung |
| `times` | Beginn/Ende jeder Tätigkeit als ISO-8601-Zeitstempel mit UTC-Offset |
| `stages` | Eindeutige Stufenkennung, positive Dauer, Gaszusammensetzung, Temperatur, Feuchte und absoluter Druck mit Messorten |
| `channels` | Bestätigte Zuordnung von CSV-Zahlenfeld, Rolle, physischem Objekt, Größe, Einheit und Messort |
| `files` | Ausschließlich ausgewählte Dateien; keine automatische Ordnerübernahme |
| `source_ranges` | Bestätigte Grenzen des Datenbereichs pro Loggerdatei mit ausdrücklich bekanntem `utc_offset` |
| `stage_ranges` | Bestätigte Datenbereiche jeder aufgenommenen Stufe, innerhalb der Laufbereiche |
| Bestätigungen | Laufbezogener Aufbau und Datei-/Laufzuordnung mit eigener Begründung/Beleg |
| `reference_assessment` | Fachlich bestätigte Referenzgrundlage und ihr Geltungsbereich; kein automatisch erteilter Kalibrierstatus |

Datenbereiche zählen **Datenrecords ab 1**, ohne Kopfzeile und ohne wiederholte
Kopfzeilen. Das ist nicht die physische Textzeilennummer bei CSV mit mehrzeiligen
Feldern. Das Original wird nicht gekürzt oder verändert.

Ein schematischer Bereich — Zahlen nur nach tatsächlicher Zuordnung setzen:

```json
{
  "source_ranges": [
    {"file": "data/measurements/mein_lauf.csv", "first_record": 1, "last_record": 600, "utc_offset": "+01:00", "confirmed": true}
  ],
  "stage_ranges": [
    {"stage_id": "S1", "file": "data/measurements/mein_lauf.csv", "first_record": 1, "last_record": 300, "confirmed": true},
    {"stage_id": "S2", "file": "data/measurements/mein_lauf.csv", "first_record": 301, "last_record": 600, "confirmed": true}
  ]
}
```

Bei bewusst **ungeregelter** Temperatur oder Feuchte `controlled: false`,
`uncontrolled_reason` und den Messort angeben; keinen Sollwert eintragen.
Die beobachtete Größe bleibt über die dokumentierten Kanäle nachvollziehbar.
Jeder ausgewählte Quelldatensatz muss nach Anwendung des bestätigten UTC-Offsets
innerhalb des angegebenen Messlaufs liegen. Eine Zeitrückstellung innerhalb des
ausgewählten Bereichs wird in diesem ersten Uploadweg gesperrt; die Reihenfolge
wird nicht umsortiert und ein Offsetwechsel nicht geraten.
Für Feuchte gelten `%RH` für relative Feuchte, `degC` für Tau-/Frostpunkt und
`umol/mol` für den Stoffmengenanteil von Wasser. Umrechnungen erfolgen nicht stillschweigend.

Die **Ziele bleiben zentral** in `config/playground_test_target.json`:

```json
{
  "gasi_workflow": {
    "host": "https://playground.datastore.bam.de",
    "approved_scope": {
      "approved": false,
      "reference": "",
      "lab_path_prefix": ""
    },
    "targets": {
      "preparation": {"space": "", "project": "", "collection": ""},
      "measurement": {"space": "", "project": "", "collection": ""},
      "analysis": {"space": "", "project": "", "collection": ""}
    }
  }
}
```

Nur diesen Abschnitt ergänzen, bestehende Testziele und `gasi_inventory` erhalten.
Der freigegebene Projektpräfix hat die Form `/8.1_.../PROJEKT`; jeder Zielpfad liegt
darunter. `approved_scope.reference` dokumentiert den konkreten lokalen Auftrag,
ersetzt keine organisatorische BAM-Freigabe. Die Collections müssen bereits existieren.
Das Notebook legt keine Spaces, Collections, Rollen, Typen oder Wertelisten an.

## Was geschrieben wird

Der erste vollständige Uploadweg umfasst **einen Sensor und einen Messlauf**.
Sensor und Ressourcen existieren bereits; Notebook 08 legt keine neue Sensoridentität an.
Mehrere Sensor-Kanäle sind möglich. Sammelauswertungen mehrerer Läufe sind im
Konzept möglich, im ersten Uploadweg aber noch nicht implementiert.

| Eintrag / Datei | Ziel / Beziehung |
|---|---|
| Vorbereitung, `EXPERIMENTAL_STEP` | Konfigurierte Vorbereitungs-Collection; SOP-Objekte gegebenenfalls Parents |
| `plan.json` und ausdrücklich gewählte Vorbereitungsdateien | `ATTACHMENT` an Vorbereitung; enthält Sensorbezug und nominelles Belastungsprofil |
| Beaufschlagung/Messung, `EXPERIMENTAL_STEP` | Konfigurierte Messlauf-Collection; Vorbereitung, Sensor, Geräte/Referenzen und Gasquellen sind Parents |
| Ausgewählte Original-Loggerdateien | Je `RAW_DATA` an Messung, bytegenau unverändert |
| `context.json` | `ATTACHMENT` an Messung; Aufbau-/Kanalbezüge, Messorte, Zeitbezug, Aufnahmeversion und bestätigte Datenbereiche |
| Auswertung, `EXPERIMENTAL_STEP` | Konfigurierte Auswertungs-Collection; Messung und gegebenenfalls Auswertesoftware sind Parents |
| Ergebnisdateien, Bericht und gegebenenfalls Code | Je `ATTACHMENT` an Auswertung; weitere Spezialtypen erst nach Schemaabgleich |
| `analysis_context.json` | `ATTACHMENT` an Auswertung; Auswerteversion und exakte Eingabedataset-Namen, erzeugender Objektcode und SHA-256 |

Die Vorbereitung hat in diesem Uploadweg immer ein eigenes Prüfplandataset.
Die generelle Vereinfachungsregel „Vorbereitung ohne eigene Dateien integrieren“
erfordert daher hier keine zusätzliche Variante.

Die lokalen Pakete liegen ausschließlich unter
`.local_playground_test/gasi_runs/<stabile Kennung>/<Manifest-Hashpräfix>/`.
Erlaubte Dateiquellen sind `data/measurements/`, `data/results/` und `docs/`.
`.env`, Konfigurationen, Geräteunterlagen und Pfade außerhalb des Repositorys
werden nicht als Uploaddateien zugelassen. Öffentliche Modell-HTML/SVG/Markdown
können ausdrücklich als Vorbereitungsdateien ausgewählt werden.

RAW_DATA durchläuft nochmals die vorhandene GaSi-CSV-Prüfung: Zeilenform,
Zahlen einschließlich NaN/Inf, Zeit-/JSON-Felder und 252-Spalten-Schema.
Alle ausgewählten Zahlenkanäle und Record-Grenzen werden am Originalinhalt geprüft.
Jeder ausgewertete Kanal braucht gültige Messwerte im gewählten Bereich.
Für den Gasfeuchtesensor muss mindestens eine gemeinsame Aufnahme von Sensorantwort
und Feuchtereferenz vorhanden sein. Dies prüft die Vollständigkeit, nicht die
messtechnische Güte: Referenzeignung, Gerätestatus, Stabilitätskriterien und
Unsicherheit bleiben Gegenstand der ausdrücklich dokumentierten fachlichen Bewertung.
Andere Rohdatenformate brauchen zuerst einen passenden Validator.

## Schreiben, Wiederholen und Verifizieren

**Run All bleibt eine lokale Vorschau.** Der Schreibaufruf benötigt in der letzten
Zelle `UPLOAD_ENABLED = True` und die genaue dort angegebene Bestätigungsphrase.
Er liest Laufkonfiguration, Ziele, Playground-Host, vorhandene Ressourcen,
Collections, Typ-Assignments, Pflichtfelder und relevante Wertelisten erneut.
Der Paket-Hash muss mit der zuvor angezeigten Vorschau übereinstimmen.
Änderungen seit der Vorschau erfordern eine erneute Prüfung.

Stabile Objektcodes und Dataset-Namen verhindern Dubletten bei serieller
Wiederholung. Ein gespeicherter Teilstand wird ergänzt; verlorene Serverantworten
nach einem erfolgreichen Speichern sind im Test berücksichtigt.
Vorhandene Metadaten und Dateien müssen zur Konfiguration passen.
Unpassende zusätzliche Parents, abweichende Hashes oder geänderte Messbedingungen
führen zum Abbruch. Es werden keine vorhandenen Ergebnisse automatisch ersetzt.

Eine **neue `analysis_id`** erzeugt einen neuen Auswertungsschritt und verwendet
unveränderte Vorbereitung und Messung erneut. Änderungen an Erfassungsbedingungen,
Sensor, Quelldaten oder bestätigtem Aufbau benötigen eine neue fachliche Laufkennung.
Nur ein schreibender Kernel pro Lauf; keine parallelen Uploads desselben Laufs.

Alle Tätigkeiten und Parents werden zurückgelesen. Jedes Dataset wird nach
dem Speichern beziehungsweise Wiederfinden erneut geladen und seine Datei
heruntergeladen. SHA-256, zugehöriger Arbeitsschritt und Ziel-Collection werden
geprüft. IDs, Collections und Browserlinks erscheinen nach Erfolg; der vollständige
Nachweis bleibt lokal als `verification.json` beim Paket.

## Prüfstand und Grenzen

Lokal geprüft: leere und vollständige Konfiguration, eindeutiger Sensorbezug,
Gas-/Temperatur-/Feuchtegrößen, CSV-/Kanal-/Bereichsprüfung, Host-/Zielsperren,
Dateiintegrität, kompletter Parent-Graph, Dataset-Zuordnung, Rückdownload,
Wiederholung und Wiederaufnahme nach bereits gespeichertem Teilstand.
Neue Auswertungen verwenden im Test dieselbe Messung wieder.

**Nicht neu live bestätigt:** zusätzliche Typ-Assignments für Sensoren/Gasquellen,
konkrete Ressourcen und Forschungsziele, Schreibrechte und Instanz-Validatoren.
Der verfügbare Session-Zugang reichte beim erneuten Versuch nicht für eine Verbindung.
Notebook 00 erneuert den Token verdeckt; Notebook 04 liest den Bestand anschließend neu.
Echte Loggerdaten wurden bei der Entwicklung nicht hochgeladen.
