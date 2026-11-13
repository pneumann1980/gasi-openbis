# GaSi: Messung jetzt erfassen, Auswertung später ergänzen

## Zwei unabhängige Einstiege

**Notebook 08** erfasst einen Messlauf mit Originalen und Kontext.
**Notebook 09** ergänzt später eine Auswertung zu einer oder mehreren bereits
registrierten Messungen. Beide starten mit frischem Kernel. Run All bleibt
Vorschau; jeder Schreibaufruf braucht Aktivierung und Bestätigungsphrase.

| Schritt | Pflichtziel | Dateien / Beziehungen |
|---|---|---|
| Messung, 08 | `gasi_workflow.targets.measurement` | RAW_DATA; Plan, Kontext und Server-Quellmanifest als ATTACHMENT. Sensor, Ressourcen und ggf. vorhandene Vorbereitung sind Parents. |
| Vorbereitung, optional | `targets.preparation` nur bei Neuanlage | Eigenständig freigegebener/wiederverwendbarer Plan; Vorbereitung ist Parent der Messung. |
| Auswertung, 09 | `targets.analysis` | Ergebnisse und Auswertemanifest als ATTACHMENT. Verwendete Messungen und Software sind Parents. |

Das automatische `plan.json` allein begründet keinen eigenen Vorbereitungsschritt.
Allgemeine Modellgrafiken sind Projektdokumentation; zum Lauf gehört der tatsächlich
verwendete Prüf-/Aufbauplan. Es werden keine Sensoridentitäten, Spaces, Collections,
Typen oder Wertelisten automatisch angelegt.

## Fachliche Zuordnung

Das Prüfobjekt („Sample“) ist ein vorhandener Gas-/Gasfeuchtesensor. Es behält
seine Identität über die Beaufschlagung und Messstufen. Vorhandenes INSTRUMENT
wiederverwenden oder SAMPLE/TEST_OBJECT anhand ihrer Pflichtfelder auswählen.
Gasquellen sind Materialien; Gaszusammensetzung, T, Feuchtegröße, Druck und Dauer
sind Bedingungen. Soll, Referenz und Sensorsignal bleiben getrennt.

Relative Feuchte benötigt Temperatur- und Wasser-/Eisbezug; Taupunkt, Frostpunkt
und Stoffmengenanteil sind andere Größen. Kammer-, Gas- und Sensortemperatur sind
nicht gleichzusetzen. Eine Rezeptkonzentration ist kein unabhängig gemessener Wert.
Die farbige [Konzeptansicht](GaSi_Konzeptmodell.html) zeigt diese Unterscheidungen.

## Messung konfigurieren

[Leere Vorlage](../config/gasi_run.example.json) → lokale `config/gasi_run.json`.
Notebook 08 kopiert nur eine fehlende Datei. Erforderlich sind Laufkennung, Zweck,
Person, Sensor-ID, Ressourcen, Aufnahmeversion, Messzeiten mit UTC-Offset, Aufbau,
Kanäle mit Größe/Einheit/Messort, Stufen und explizite Dateien/Record-Bereiche.
Ergebnisse, Auswertungskennung/-zeiten/-software und Auswertungsziel sind nicht
erforderlich. Eine noch nicht abgeschlossene Referenzbewertung bleibt im Kontext
als offen erhalten und verhindert nicht die Erfassung der Originale.

`preparation.mode`:

- `inline`: Plan/Sollprofil am Messlauf; Standard.
- `create`: eigenes Ziel und Zeiten; `justification` und
  `independently_released=true` oder `reused_across_runs=true` erforderlich.
- `reuse`: vorhandene EXPERIMENTAL_STEP-`identifier` als Parent, kein neues Vorbereitungsziel.

Ziele bleiben zentral in `config/playground_test_target.json`. Geprüft wird nur
das jeweils benötigte Ziel unter dem ausdrücklich freigegebenen Laborbuchprojekt.
Die lokale Auftragsreferenz ersetzt keine organisatorische BAM-Freigabe.

Original-CSV bleiben bytegleich. Es gelten die bestehenden Prüfungen des
252-Spalten-Loggers: Zeilenform, endliche Zahlen, Zeiten/JSON und zugeordnete Kanäle.
`source_ranges` umfassen `file`, `first_record`, `last_record`,
`utc_offset` und `confirmed=true`. `stage_ranges` ergänzen `stage_id`.
Records zählen ab 1 ohne Kopfzeilen, nicht physische Textzeilen.
Ein Lauf kann mehrere Dateien umfassen. Unaufgelöste Uhrumstellungen werden
gesperrt; Originalzeitstempel und Reihenfolge bleiben erhalten.

`reference_evidence` ordnet verwendete Nachweise dem tatsächlichen Gerät bzw.
der Gascharge zu: `resource_id`, `document_reference`, `scope` und
ggf. `conditions` / vorhandene `calibration_id`.

## Eine Datei mit mehreren Läufen

Fundstelle im lesend geprüften Betriebscode: `logger/measurement_logger.py`,
`write_sample` und `_prepare_candidate`. Der Logger schreibt tagesbezogen im
Append-Modus. Tageswechsel und Wiederherstellungsdateien können einen Lauf auf
mehrere Dateien verteilen. `datetime.now()` liefert hier keinen UTC-Offset.
Eine verlässliche fachliche Lauf-ID ist in der CSV nicht enthalten.

31 lokale Dateien wurden geprüft; sieben enthalten wechselnde Automatikzustände.
Das ist ein Hinweis auf mögliche gemeinsame Nutzung, kein Nachweis der Anzahl
fachlicher Läufe. Lokaler Detailbefund:
`.local_playground_test/prompt-review/file_boundaries.json`.

**Pilot:** `raw_file_policy.mode=exclusive_run` mit bestätigtem Beleg.
`shared_sources` zeigt betroffene `file` und `run_ids` in der Vorschau;
solche Dateien bleiben schreibgesperrt. Schon von einem anderen GaSi-Messobjekt
registrierte RAW_DATA-Hashes werden nicht erneut hochgeladen.

Vorgesehene gemeinsame Ablage: **ein erfassendes Aufnahmeobjekt besitzt das
Original einmalig**. Mehrere fachliche Läufe referenzieren dieselbe Dataset-ID
mit ihren eigenen Record-Bereichen; Aufnahme → Lauf als Objekt-Parent-Beziehung.
Diese vollständige Zuordnung ist noch synthetisch live abzunehmen. Bis dahin
ist dieser Fall nicht zum Schreiben freigegeben. Native Dataset-Parents allein
lösen die Zuordnung eines Originals zu mehreren fachlichen Läufen nicht.

## Server-Quellmanifest

Nach RAW_DATA-Registrierung/Rücklesen legt Notebook 08 `source_receipt.json` als
ATTACHMENT an der Messung ab: tatsächliche Server-Dataset-ID/Code und relativer
Dateipfad, Original-SHA-256, Record-/Stufenbereiche, UTC-Offset, Messzeiten,
Ressourcen, Kanäle und Referenznachweise. Die lokale `verification.json` enthält
dieselben Eingabezeiger. Ein fehlendes Quellmanifest wird bei Wiederaufnahme
ergänzt; abweichende vorhandene Inhalte werden nicht überschrieben.

## Spätere Auswertung

[Leere Vorlage](../config/gasi_analysis.example.json) → `config/gasi_analysis.json`.
Notebook 09 braucht keine lokale Laufkonfiguration oder lokalen Rohdaten.
`inputs` übernehmen aus dem Quellmanifest `measurement_id`, `dataset_id`,
`file_path` und `sha256`; eigene `source_ranges`/`stage_ranges` beschreiben
die wirklich verwendete Teilmenge. Mehrere Bereiche und mehrere Messungen sind möglich.

Zusätzlich: eigene `analysis_id`, Zweck/Person/Zeiten, Code bzw. Version,
`parameters`, `selection_rules` und Ergebnisdateien. Für `calibration` sind
Nachweise/Bezugsbedingungen, stabile Fenster und Messunsicherheit erforderlich.
Für `conformity` zusätzlich Grenzwerte mit Einheiten und Entscheidungsregel.
Unbewertete Unsicherheit bei reiner Charakterisierung bleibt als fehlend erkennbar.

Vor jedem Schreiben: Server-Quellmanifest und RAW_DATA erneut lesen, Originaldatei
herunterladen, Hash und Eigentümer prüfen. Die Auswahl muss Teilmenge der
registrierten Record-/Stufen-/Zeitbereiche sein. Grenzzeitstempel werden in UTC
im Manifest festgehalten. CALIBRATION-Verweise werden gegen das Referenzgerät geprüft.

`analysis_manifest.json` enthält die aufgelösten Server-IDs/Pfade, Hashes, Auswahl,
Zeitfenster, Nachweise, Parameter und Regeln. Jede eigenständige Auswertung erhält
eine neue Kennung und verwendet bestehende Messungen/Rohdaten erneut.

## Native Dataset-Parents

Die [pyBIS-API](https://openbis.readthedocs.io/en/20.10.12-plus/software-developer-documentation/apis/python-v3-api.html#get-set-add-and-remove-parent-datasets)
stellt `add_parents`, `save` und `get_parents` bereit. Im Testclient ist
Ergebnisdataset → Eingabedataset geprüft. Die Live-Probe wurde vor jeder Mutation
abgebrochen: Die konfigurierte Laborbuch-Testcollection ist aktuell nicht lesbar.
`native_dataset_parents=false` bleibt Standard. Aktivierung erfordert
`gasi_workflow.native_dataset_parents.confirmed=true` und `evidence` eines
erfolgreichen synthetischen Instanztests. Das präzise Manifest bleibt auch dann nötig.

## Suche und Browser-Abnahme

| Gesucht | Vorhandene Properties / Beziehungen |
|---|---|
| Laufkennung | `$NAME` enthält Kennung; zusätzlich `REFERENCE` |
| Prüfzweck | `EXPERIMENTAL_STEP.EXPERIMENTAL_GOALS` |
| Datum | `START_DATE` / `END_DATE` |
| Prüfling | Sensor als Parent; dessen Children/Hierarchie zeigt den Lauf |
| Kanal, Messort, Stufen, Bereiche | `context.json` und Server-Quellmanifest |

Diese Properties sind lesend bestätigt. Eine Masterdata-Erweiterung ist für den
Pilot nicht erforderlich. Erst eine gewünschte instanzweite kanalweise Zahlenabfrage
wäre eine konkrete neue Suchlücke.

Browser-Abnahme nach bewusst aktiviertem Pilot:

1. Sensor über vorhandene ID öffnen → Children/Hierarchie → Messlauf.
2. Im Laborbuch Laufkennung/REFERENCE, Zweck und Messdatum suchen.
3. Sensor-/Ressourcen-Parents, RAW_DATA, konkreten Plan und Kontext prüfen.
4. Quellmanifest: Dataset-ID, Pfad, Hash und Record-Bereich mit Original vergleichen.
5. Spätere Auswertung öffnen → Parents führen zu allen verwendeten Messungen.
6. Ergebnis und `analysis_manifest.json` öffnen → exakte Eingaben, UTC-Fenster,
   Auswahlregeln und Referenznachweise nachvollziehen.
7. Nach nativer Live-Abnahme zusätzlich Dataset-Parent-Graph prüfen.
8. Wiederholung: keine neuen Rohdaten/Messungen; neue Auswertung nur mit neuer analysis_id.

Aktueller Stand und Pilotlücken: [GaSi_Projektstatus.md](GaSi_Projektstatus.md).
In diesem Auftrag wurden keine echten Messdaten hochgeladen.
