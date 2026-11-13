# Projektstatus GaSi: Erfassung und spätere Auswertung

## Ergebnis dieses Auftrags

Messung und Auswertung sind unabhängig nutzbar. Notebook 08 braucht weder
Auswertungskennung noch Ergebnisse/Auswertungsziel. Der Plan liegt standardmäßig
am Lauf; eine eigenständige Vorbereitung benötigt Freigabe-/Wiederverwendungsgrund
oder eine vorhandene Objekt-ID. Notebook 09 wertet später eine oder mehrere
registrierte Messungen aus.

Der aktuelle Stand ist **für einen eindeutig zugeordneten Pilotlauf lokal geprüft,
aber noch nicht als Forschungsupload in der Instanz abgenommen**.
Ein echter Messdaten-Upload wurde in diesem Auftrag nicht ausgeführt.

## Aktuell live gelesen

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
3. **Aufbau/Kanäle:** aktuelle Positionen, Sensorantwort, Referenz, Messorte, Einheiten,
   Feuchtegröße und Temperatur-/Druckbezug bestätigen. Die Inventarregistrierung
   bestätigt keinen aktuellen Einbau.
4. **Originale/Laufgrenzen:** einen eindeutig zuordenbaren Lauf, tatsächliche
   Dateien, Daten-/Stufenbereiche und belegten UTC-Offset festlegen.
5. **Ressourcen:** tatsächliche Geräte/Referenzen, Gasflaschen/Chargen und
   verwendete Nachweise samt Geltungsbereich auswählen.
6. **Messung abnehmen:** zunächst ein synthetischer Lauf im nun bestätigten
   Ziel; anschließend bewusst ausgelöster echter Pilot. Run All bleibt Vorschau.
7. **Spätere Auswertung:** eigenes Ziel, analysis_id, Code/Version, echte Eingabeauswahl
   und Ergebnisse; fachlich nötige stabile Fenster, Unsicherheit und Entscheidungsregel.
8. **Zusatzfälle:** native Dataset-Parents und gemeinsame Dateibesitzer separat
   synthetisch live testen; bis dahin nicht als bestätigt behandeln.

## Prüfungen und Bedienfolge

**Bestanden:** 109 Tests sowie alle 13 GaSi-Notebooks in frischen Kernels
(30 lokale Durchläufe einschließlich Workshop-Einrichtung). Alle
Notebook-Schreibaufrufe liefen ausschließlich gegen Testclients. Die 31
Original-CSVs blieben laut SHA-256 unverändert.

Lokal: unabhängige Messung ohne Vorbereitung/Auswertung, optional neue/benutzte
Vorbereitung, spätere Auswertung in frischem Kontext, mehrere Dateien und mehrere
Messungen, Dubletten-/Shared-File-Sperre, Wiederholung, gespeicherte Teilfehler,
exakte Rückverfolgung Ergebnis → Manifest → Serverdataset → Originalbereich.
Schreiben ist in beiden Notebooks standardmäßig ausgeschaltet.

**Bedienfolge:** 00 Session bei Bedarf → 04 aktuellen Bestand lesen →
02/06 Aufbau/Identitäten prüfen → 03 Originale validieren → 08 Messung erfassen.
**Später unabhängig:** 09 Auswertung ergänzen. 01 erzeugt aktuelle Projektgrafiken.
07 wird nur für noch fehlende belegte Geräteidentitäten benötigt.

Der [Browser-Abnahmetest](GaSi_Forschungsupload.md#suche-und-browser-abnahme)
führt vom Sensor und der Laborbuchsuche zum Messlauf und von der Auswertung bis
zur exakten unveränderten Eingabe.

## Geänderte Bestandteile

- [gasi_run.py](../gasi_run.py), [gasi_analysis.py](../gasi_analysis.py): getrennte Abläufe, bedarfsabhängige Ziele,
  Server-Quellmanifest und präzise Auswerteprovenienz.
- [Notebook 08](../GaSi_08_Forschungsablauf_hochladen.ipynb),
  [Notebook 09](../GaSi_09_Auswertung_hochladen.ipynb),
  [Laufvorlage](../config/gasi_run.example.json),
  [Auswertungsvorlage](../config/gasi_analysis.example.json) und
  [zentrale Zielvorlage](../config/playground_test_target.example.json).
- Datenmodell, Konzept, Forschungsuploadbeschreibung, HTML/SVG, README und Git-Ausschlüsse.
- Tests für getrennte Abläufe, Herkunft, Auswahl, Teilfehler, Originalschutz und frische Kernels.

Lokale Gerätebelege, Credentials, Lauf-/Auswertungskonfigurationen und echte
Mess-/Ergebnisdateien bleiben außerhalb von Git. Vorhandene lokale Notebook-Zustände
des Nutzers bleiben erhalten.
