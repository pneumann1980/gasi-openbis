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

**Bestanden:** 128 Unit-Tests, alle fünf verbleibenden Notebooks in 17 frischen
Kernels mit gesperrtem Netzwerk. Paketinstallation simuliert, echte Paketimports;
Schreiben nur gegen synthetische Testclients. Einrichtung, Prüfling und Upload
einschließlich Wiederholung geprüft. Zwei zusätzliche Kernel-Prüfungen testen
den fertigen Formularablauf mit False/True und Wiederholung. 31 Original-CSVs unverändert.
Die neue gebündelte Einrichtung wurde in diesem Schritt nicht live schreibend
ausgeführt. Die folgenden Live-Befunde stammen aus dem vorherigen lesenden Abgleich.

## Geführte Laufvorbereitung: erster Entwurf

Notebook 03 öffnet ein Formular. Dateien einlesen, Records/Zeitbasis auswählen,
Prüfling/Zweck/Person angeben und die Zugehörigkeit der Originale festlegen.
Geräte, Aufbauhinweis und Prüflingskanal lassen sich optional zuordnen.
Ein leeres Kennungsfeld wird aus Prüfling und ausgewählten Daten stabil befüllt.
Speichern bleibt lokal und sichert den vorherigen Konfigurationsstand;
gleichzeitige Änderungen werden erkannt. Erst **Messung ausführen** verwendet
den zentralen Sessionmodus. Run All öffnet auch bei True lediglich das Formular.

Das Profil `raw_capture` dokumentiert unbekannte Aufnahmeversion, Ressourcen,
Kanäle und Messbedingungen als `metadata_gaps` im Kontext und Quellmanifest.
Der openBIS-Name kennzeichnet die Rohdatenerfassung. Sensoridentität, tatsächliche
Record-Zuordnung, UTC-Offsets und exklusive Originalzugehörigkeit bleiben nötig.
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

## Letzter dokumentierter Live-Lesebefund

| Befund | Status |
|---|---|
| Playground-Verbindung | In diesem Auftrag erfolgreich; vorherige Verbindungsfehler sind kein aktueller Befund mehr |
| `/8.1_EQUIPMENT/GASI/INSTRUMENTS` | Sichtbar, zehn Objekte |
| `/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS` | Sichtbar, ein Objekt |
| `/8.1_PNEUMANN/GASI_TEST/RUNS` | Aktuell nicht lesbar und nicht im sichtbaren Collection-Katalog |
| Aktuelle Forschungs-Schreibrechte | Nicht bewiesen; Sichtbarkeit/lesendes Schema reichen nicht |
| Native Dataset-Parents | API dokumentiert und Testclient geprüft; Live-Probe vor jeder Mutation am fehlenden Laborbuchziel gesperrt |
| Gemeinsame Originaldatei für mehrere Läufe | Vorschlag dokumentiert, Schreiben bis vollständiger Live-Abnahme gesperrt |

Es ist nicht geklärt, ob die Laborbuchcollection entfernt wurde oder mit der
aktuellen Session nicht sichtbar ist. Sie wurde nicht automatisch neu angelegt.
Die alten synthetischen Live-Erfolge sind historische Nachweise.
Lesende Details liegen lokal unter
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

1. **Laborbuchziel:** Testcollection-Lesbarkeit klären oder konkrete freigegebene
   Mess- und später Auswertungscollection auswählen. Ziele zentral konfigurieren;
   Vorbereitung nur bei eigenständiger Registrierung.
2. **Prüfling:** den tatsächlichen Gas-/Gasfeuchtesensor identifizieren, vorhandene
   Objekt-ID verwenden oder ihn einmalig mit fachlich passendem Typ registrieren.
3. **Aufbau/Kanäle:** bekannte Positionen, Sensorantwort, Referenz, Messorte und
   Bezugsbedingungen zuordnen; ungeklärte Angaben im Rohdatenprofil offen halten.
   Vor einer fachlichen Bewertung klären. Die Inventarregistrierung bestätigt keinen Einbau.
4. **Originale/Laufgrenzen:** einen eindeutig zuordenbaren Lauf, tatsächliche
   Dateien, Datenbereiche und belegten UTC-Offset festlegen; Messstufen nur übernehmen, wenn belegt.
5. **Ressourcen:** tatsächliche Geräte/Referenzen, Gasflaschen/Chargen und
   verwendete Nachweise samt Geltungsbereich auswählen.
6. **Messung abnehmen:** zunächst ein synthetischer Lauf im nun bestätigten
   Ziel; anschließend bewusst ausgelöster echter Pilot. Run All bleibt Vorschau.
7. **Spätere Auswertung:** eigenes Ziel, analysis_id, Code/Version, echte Eingabeauswahl
   und Ergebnisse; fachlich nötige stabile Fenster, Unsicherheit und Entscheidungsregel.
8. **Zusatzfälle:** native Dataset-Parents und gemeinsame Dateibesitzer separat
   synthetisch live testen; bis dahin nicht als bestätigt behandeln.

## Prüfungen und Bedienfolge

Der vorherige Stand war mit 109 Tests / 13 Notebooks geprüft. Die aktuellen
Zahlen der Vereinfachung stehen oben. Alle
Notebook-Schreibaufrufe liefen ausschließlich gegen Testclients. Die 31
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
