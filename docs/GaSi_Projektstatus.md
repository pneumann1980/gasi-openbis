# Projektstatus GaSi: Erfassung und spätere Auswertung

## Vereinfachte Bedienung

Im Hauptordner bleiben drei Arbeitsnotebooks: **Session starten**, **Einmalig
einrichten** und **Messdaten hochladen**. **Prüfling verwalten** ist separat.
Die optionale spätere Auswertung liegt im Unterordner `notebooks/`.
Einrichtung, Zielkonfiguration, Geräteinventar und synthetischer Schreibtest sind
zusammengeführt. Die zentrale Konzept-HTML, die ausführliche Datenmodell-HTML und
vier Konzept-SVGs werden über eine separat ausführbare Offline-Zelle der Einrichtung erzeugt.
Die zusätzliche einfache HTML entfällt. Diese Bereinigung ist mit 16 HTML-/SVG-Tests
und dem Einrichtungsnotebook in einem frischen Kernel geprüft.
Auch der alte Aufruf in einem bereits geöffneten Notebook funktioniert nach dem
Neuladen der Module; er erzeugt keine zusätzliche einfache HTML.

**Ein Schalter:** `SCHREIBEN = False/True` ausschließlich im Session-Notebook.
Der lokale Modus in `.env` wird von jedem Arbeitsaufruf neu gelesen; er gilt auch
über Kernel-Neustarts bis zur nächsten Änderung in der Session. Es gibt keine
Confirmation-Strings oder weiteren lokalen Schreibfreigaben. Fachliche Belege,
Pflichtfelder, Zielgrenzen und serverseitige Rechte bleiben erforderlich.

**Bestanden:** 137 Unit-Tests, alle fünf verbleibenden Notebooks in 21 frischen
Kernels mit gesperrtem Netzwerk. Paketinstallation simuliert, echte Paketimports;
Schreiben nur gegen synthetische Testclients. Einrichtung, Prüfling und Upload
einschließlich Wiederholung geprüft. Sensorprüfung, Anlagenlauf und ungeklärter
Prüflingsbezug wurden mit False/True geprüft. Zwei weitere frische Kernels prüfen
die tatsächlichen Upload-/Prüflingsnotebooks mit gesperrter Verbindung; der
Vier-Dateien-Entwurf besteht die lokale Vorschau. 31 Original-CSVs und die
Sessiondatei unverändert. Echte Messdateien wurden nicht hochgeladen.

## Formularfehler und Anlagenlauf ohne Prüfling: 13.11.2026

Die vier Originale waren zugeordnet. Eine unaufgelöste Prüflingsbezeichnung war
jedoch noch keine openBIS-ID; dadurch fehlte auch die abgeleitete Laufkennung.
Die bisherige Meldung forderte irreführend erneut die Dateiauswahl. Das Formular
zeigt jetzt die konkrete Ursache dauerhaft an und kann bestehende Prüflinge
lesend nach Name, Code, PermID oder Objektlink auflösen.

Laut Nutzer war vermutlich kein externer Prüfling beteiligt. Der lokale Entwurf
ist deshalb vorsichtig als `measurement_subject=unresolved` gespeichert, mit
stabiler Laufkennung und ohne erfundene Sensor-ID. Die vier Dateien, ihre
Record-/Zeitzonenzuordnung und Hashbindung bleiben erhalten. `system` ist die
Wahl für einen bestätigten Anlagenlauf ohne externen Prüfling; `sensor` benötigt
eine tatsächliche Sensoridentität. Kontext, Quellmanifest und spätere Auswertung
führen diese Unterscheidung mit. Die grüne Sensorbox im Modell ist optional.

**Live bestätigt:** `GASI_TEST_SYSTEM_CAPTURE_V1`, ausschließlich synthetisch,
ein `EXPERIMENTAL_STEP` ohne Sensor-Parent in
`/8.1_PNEUMANN/GASI_TEST/RUNS`. RAW_DATA, Plan, Kontext und Server-Quellmanifest
wurden heruntergeladen und per SHA-256 geprüft. Der nach Objekterstellung
unterbrochene Versuch wurde mit derselben Kennung vervollständigt; ein weiterer
Durchlauf verwendet Objekt und Datasets unverändert wieder.

Beim Rücklesen zeigte sich ein echter Zeitstempelfehler: ISO-Eingaben wurden
als lokale Uhrzeit interpretiert, und das Serverformat ließ sich nicht einlesen.
Der getestete Übertragungswert `2026-11-13 10:00:00 +0000` kommt korrekt als
`2026-11-13 11:00:00 +0100` zurück. Messung und Auswertung verwenden jetzt dieses
explizite Offsetformat; Rücklesen vergleicht den Zeitpunkt. Subsekunden in den
openBIS-Zeitfeldern bleiben bis zur Bestätigung gesperrt und werden nicht gerundet.

Synthetischer Browsernachweis:
[Messlauf](https://playground.datastore.bam.de/openbis/webapp/eln-lims/?viewName=showViewSamplePageFromPermId&viewData=20261113161936642-19376),
[RAW_DATA](https://playground.datastore.bam.de/openbis/webapp/eln-lims/?viewName=showViewDataSetPageFromPermId&viewData=20261113163118651-19380).
Lokale Prüfdetails: `.local_playground_test/upload-diagnosis/` (ignoriert).

## Geführte Laufvorbereitung: erster Entwurf

Notebook 03 öffnet ein Formular. Dateien einlesen, Records/Zeitbasis auswählen,
Laufart, gegebenenfalls Prüfling, Zweck/Person und Zugehörigkeit der Originale festlegen.
Geräte, Aufbauhinweis und Prüflingskanal lassen sich optional zuordnen.
Ein leeres Kennungsfeld wird aus Laufart, gegebenenfalls Prüfling und ausgewählten Daten stabil befüllt.
Speichern bleibt lokal und sichert den vorherigen Konfigurationsstand;
gleichzeitige Änderungen werden erkannt. Erst **Messung ausführen** verwendet
den zentralen Sessionmodus. Run All öffnet auch bei True lediglich das Formular.

Das Profil `raw_capture` dokumentiert unbekannte Aufnahmeversion, Ressourcen,
Kanäle und Messbedingungen als `metadata_gaps` im Kontext und Quellmanifest.
Der openBIS-Name kennzeichnet die Rohdatenerfassung. Sensoridentität bleibt für
Sensorprüfungen nötig; Anlagenläufe und ungeklärter Bezug erhalten keinen
Sensor-Parent. Tatsächliche Record-Zuordnung, UTC-Offsets und exklusive
Originalzugehörigkeit bleiben nötig.
CSV-Profile und Logabschnitte sind Vorschläge; es entstehen keine erfundenen Stufen.
Bei bereits beschriebenen Läufen bleiben bekannte Stufen, Referenzen, Kanäle und
Zeitgrenzen bei unveränderter Quellzuordnung erhalten.

Zusätzlich lokal gelesen: Formular mit 31 CSVs und zehn Geräteoptionen; eine
vorhandene Datei technisch geprüft. Keine openBIS-Verbindung,
keine Änderungen an Originalen, Laufkonfiguration oder Sessiondatei.

**Grenze des Entwurfs:** Nachträgliche Ergänzungen bereits hochgeladener
Laufmetadaten sind noch kein eigener Ablauf. Geänderte Metadaten derselben
Kennung bleiben gegen Überschreiben gesperrt. Gemeinsame Originale mehrerer
Läufe bleiben bis zur entsprechenden Live-Abnahme gesperrt.

## Messung und spätere Auswertung

Messung und Auswertung sind unabhängig nutzbar. Das Messdaten-Notebook braucht weder
Auswertungskennung noch Ergebnisse/Auswertungsziel. Der Plan liegt standardmäßig
am Lauf; eine eigenständige Vorbereitung benötigt Freigabe-/Wiederverwendungsgrund
oder eine vorhandene Objekt-ID. Das optionale Auswertungsnotebook ergänzt später Ergebnisse zu einer oder mehreren
registrierten Messungen.

Der aktuelle Stand ist **für einen eindeutig zugeordneten Pilotlauf lokal geprüft,
aber noch nicht als Forschungsupload in der Instanz abgenommen**.
Ein echter Messdaten-Upload wurde in diesem Auftrag nicht ausgeführt.

## Letzter dokumentierter Live-Befund

| Befund | Status |
|---|---|
| Playground-Verbindung | In diesem Auftrag erfolgreich; vorherige Verbindungsfehler sind kein aktueller Befund mehr |
| `/8.1_EQUIPMENT/GASI/INSTRUMENTS` | Sichtbar, zehn Objekte |
| `/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS` | Sichtbar, ein Objekt |
| `/8.1_PNEUMANN/GASI_TEST/RUNS` | Jetzt lesend und schreibend mit dem synthetischen Anlagenlauf bestätigt |
| Aktuelle Forschungs-Schreibrechte | EXPERIMENTAL_STEP, RAW_DATA und ATTACHMENT im genannten Testziel bestätigt; kein echter Forschungsupload ausgeführt |
| Native Dataset-Parents | API dokumentiert und Testclient geprüft; separate Live-Abnahme noch offen |
| Gemeinsame Originaldatei für mehrere Läufe | Vorschlag dokumentiert, Schreiben bis vollständiger Live-Abnahme gesperrt |

Der frühere Befund einer fehlenden Laborbuchcollection ist durch den aktuellen
Test überholt. Die begrenzte Testbereichseinrichtung wurde beim synthetischen
Versuch idempotent verwendet; im abschließenden Durchlauf waren keine neuen
Ziele nötig. Die getrennten Zusatzfälle mit nativen Dataset-Parents oder
geteilten Originalen sind damit nicht live abgenommen. Ältere lesende Details liegen lokal unter
`.local_playground_test/prompt-review/schema_status.json`,
`inventory_status.json` und `native_parent_probe.json`.

## Typen: Katalog, Schema und Schreiben getrennt

| Typ | Jetzt lesend bestätigte Pflichtfelder / Bedeutung |
|---|---|
| `EXPERIMENTAL_STEP` | Keine mandatory Assignments; NAME, REFERENCE, Zweck- und Zeitfelder vorhanden |
| `INSTRUMENT` | NAME, MANUFACTURER, BAM_OE, BAM_LOCATION_COMPLETE |
| `SAMPLE` | NAME, BAM_OE; generischer Kandidat für neuen Sensor, sofern fachlich passend |
| `TEST_OBJECT` | NAME, PRODUCTION_DATE, TEST_OBJ_STATUS, BAM_OE, TEST_OBJ_MATERIAL; fehlende Produktions-/Materialdaten nicht erfinden |
| `GAS_BOTTLE` | SUPPLIER, GAS_VOLUME, GAS_PRESSURE_BAR, BAM_OE |
| `SOP` | NAME, ID_EAKTE, LINK_EAKTE, BAM_OE, RESPONSIBLE_PERSON, CO_RESPONSIBLE_PERSON, AUTHOR, VERSION, LAST_CHECK, CHECK_INTERVAL |
| `SOFTWARE_CODE` | NAME, SOFTWARE_NAME |
| `PARAMETER_SET` | NAME; für Pilot kein eigener Typ nötig, Profil bleibt Kontext |
| `ENVIRONMENTAL_CONDITIONS` | NAME, AIR_TEMPERATURE_IN_CELSIUS, AIR_REL_HUMIDITY_IN_PERCENT; Luftbedingungen sind nicht automatisch Prozessgas-/Taupunktbedingungen |
| `CALIBRATION` | NAME, INSTRUMENT, CALIBRATION_DATE, CALIBRATION_PROVIDER, CALIBRATION_CERTIFICATE_NUMBER, ACCREDITATED_CALIBRATION_LAB |
| `RAW_DATA` / `ATTACHMENT` | Typ-Assignments lesend bestätigt; Pflichtfelder im aktuellen Befund nicht markiert |
| `TESTING_EQUIPMENT` | Nicht lesend bestätigt; keinen Ersatztyp automatisch anlegen |

Diese Typen sind damit mehr als bloße Katalogkandidaten. Ihre Eignung für konkrete
neue Objekte sowie Validatoren/Schreibrechte sind trotzdem separat zu bestätigen.
Es wurden keine Masterdata geändert. Der bestehende Inventar- und synthetische
Schreibnachweis beweist nicht alle neuen Kombinationen dieses Forschungsuploads.

## Herkunft und Auswahl

Loggerbefund: tagesbezogenes Append-Protokoll, Tageswechsel-/Recovery-Dateien,
lokale Zeit ohne Offset; keine fachliche Lauf-ID. 31 Beispiele geprüft, sieben mit
wechselnden Automatikzuständen. Daraus lässt sich keine verlässliche Zahl
fachlicher Läufe ableiten. Eine bestätigte Sitzungs-/Archivzuordnung stand für
diese Aufnahmen nicht zur Verfügung.

Für geteilte Dateien ist eine einmalige Ablage an einem erfassenden Aufnahmeobjekt
vorgesehen. Die fachlichen Läufe referenzieren dieselbe Dataset-ID mit ihren
Auswahlbereichen. Bis zur Live-Abnahme bleibt dieser Fall gesperrt.
Im Pilot werden ausschließlich eindeutig belegte Originale ausgewählt.

Das Server-Quellmanifest enthält echte Dataset-IDs/-Codes und relative Dateipfade.
Das Auswertemanifest prüft sie erneut mit Hash, Record-/Stufen-/Zeitbereichen,
Referenznachweisen, Codeversion, Parametern und Auswahlregeln. Anforderungsprüfungen
verlangen Grenzwerte, Entscheidungsregel und Unsicherheit; Messkanäle bleiben
von Rezept-Sollwerten getrennt.

## Noch nötig für den ersten echten Pilot

1. **Laborbuchziel:** Der Testbereich ist bestätigt. Für echte Forschungseinträge
   die gewünschte fachliche Ablage prüfen; die spätere Auswertung hat ein eigenes Ziel.
2. **Laufart:** Anlagenlauf ohne Prüfling oder noch ungeklärter Bezug. Nur bei
   Sensorprüfungen den tatsächlichen Sensor identifizieren und registrieren/wiederverwenden.
3. **Aufbau/Kanäle:** bekannte Positionen, Sensorantwort, Referenz, Messorte und
   Bezugsbedingungen zuordnen; ungeklärte Angaben im Rohdatenprofil offen halten.
   Vor einer fachlichen Bewertung klären. Die Inventarregistrierung bestätigt keinen Einbau.
4. **Originale/Laufgrenzen:** einen eindeutig zuordenbaren Lauf, tatsächliche
   Dateien, Datenbereiche und belegten UTC-Offset festlegen; Messstufen nur übernehmen, wenn belegt.
5. **Ressourcen:** tatsächliche Geräte/Referenzen, Gasflaschen/Chargen und
   verwendete Nachweise samt Geltungsbereich auswählen.
6. **Messung abnehmen:** Synthetischer Anlagenlauf bestanden. Den gespeicherten
   echten Entwurf bewusst über Messung ausführen hochladen. Run All öffnet nur das Formular.
7. **Spätere Auswertung:** eigenes Ziel, analysis_id, Code/Version, echte Eingabeauswahl
   und Ergebnisse; fachlich nötige stabile Fenster, Unsicherheit und Entscheidungsregel.
8. **Zusatzfälle:** native Dataset-Parents und gemeinsame Dateibesitzer separat
   synthetisch live testen; bis dahin nicht als bestätigt behandeln.

## Prüfungen und Bedienfolge

Der vorherige Stand war mit 109 Tests / 13 Notebooks geprüft. Die aktuellen
Zahlen der Vereinfachung stehen oben. Alle
Notebook-Schreibaufrufe der isolierten Abnahme liefen ausschließlich gegen Testclients. Die 31
Original-CSVs blieben laut SHA-256 unverändert.

Lokal: unabhängige Messung ohne Vorbereitung/Auswertung, optional neue/benutzte
Vorbereitung, spätere Auswertung in frischem Kontext, mehrere Dateien und mehrere
Messungen, Dubletten-/Shared-File-Sperre, Wiederholung, gespeicherte Teilfehler,
exakte Rückverfolgung Ergebnis → Manifest → Serverdataset → Originalbereich.
Schreiben wird ausschließlich in der Session eingestellt; Standard ist False.
Frühere Confirmation-Strings und lokale Freigabeschalter sind entfernt.

**Bedienfolge:** `GaSi_01_Session_starten.ipynb` →
`GaSi_02_Einmalig_einrichten.ipynb` (einmalig) →
`GaSi_03_Messdaten_hochladen.ipynb` (je Lauf).
`GaSi_Pruefling_verwalten.ipynb` wird bei neuem Sensor benötigt.
Später unabhängig: `notebooks/GaSi_Auswertung_hochladen.ipynb`.
Die Einrichtung enthält eine separat mit frischem Kernel ausführbare Offline-Zelle
für alle Modell-HTMLs, Tabellen und vier Konzept-SVGs.

Der [Browser-Abnahmetest](GaSi_Forschungsupload.md#suche-und-browser-abnahme)
führt vom Sensor und der Laborbuchsuche zum Messlauf und von der Auswertung bis
zur exakten unveränderten Eingabe.

## Geänderte Bestandteile

- [gasi_run.py](../gasi_run.py), [gasi_analysis.py](../gasi_analysis.py): getrennte Abläufe, bedarfsabhängige Ziele,
  Server-Quellmanifest und präzise Auswerteprovenienz.
- [Messdaten-Notebook](../GaSi_03_Messdaten_hochladen.ipynb),
  [Auswertung](../notebooks/GaSi_Auswertung_hochladen.ipynb),
  [Laufvorlage](../config/gasi_run.example.json),
  [Auswertungsvorlage](../config/gasi_analysis.example.json) und
  [zentrale Zielvorlage](../config/playground_test_target.example.json).
- Datenmodell, Konzept, Forschungsuploadbeschreibung, HTML/SVG, README und Git-Ausschlüsse.
- Tests für getrennte Abläufe, Herkunft, Auswahl, Teilfehler, Originalschutz und frische Kernels.

Lokale Gerätebelege, Credentials, Lauf-/Auswertungskonfigurationen und echte
Mess-/Ergebnisdateien bleiben außerhalb von Git. Vorhandene lokale Notebook-Zustände des Nutzers sind bytegleich unter
`.local_playground_test/notebooks_vor_vereinfachung_*/` gesichert; die alten
Einzelnotebooks sind aus dem Hauptordner entfernt.
