# GaSi-Playground: eingerichteter Testbereich und Live-Nachweis

**Historischer Schreibnachweis:** Bei der aktuellen lesenden Prüfung ist die
Laborbuch-Testcollection nicht mehr lesbar. Daraus wird keine aktuelle
Schreibbestätigung abgeleitet. Siehe [Projektstatus](GaSi_Projektstatus.md).

Stand: 2026-11-12T13:40:00.401078+00:00 (UTC). Ausschließlich synthetische Testeinträge.

## Festgelegte Ablage

| Zweck | Bestehender Space | Angelegtes Projekt | Angelegte Collection |
|---|---|---|---|
| Laborbuch | `8.1_PNEUMANN` | `GASI_TEST` | `/8.1_PNEUMANN/GASI_TEST/RUNS` |
| Geräteinventar | `8.1_EQUIPMENT` | `GASI_TEST` | `/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS` |

Beide Projekte tragen den Marker `GASI_PLAYGROUND_TEST_V1`. Die Collections verwenden
`COLLECTION` mit `$DEFAULT_OBJECT_TYPE=EXPERIMENTAL_STEP` bzw. `INSTRUMENT`.
Bestehende Typen, Rollen und andere Projekte wurden nicht verändert.

Die Freigabe für genau diese Testziele beruht auf dem ausdrücklichen Nutzerauftrag
in dieser Sitzung. Ihr Vermerk steht zusammen mit den Zielpfaden in der ignorierten
`config/playground_test_target.json`. Die ausführende Session hat über `8.1_ADMIN`
Bereichs-Adminrechte; es wurden keine Rollen erteilt oder Rechte ausgeweitet.

## Bestätigte Einträge

| Eintrag | Identifier / PermID | Browser |
|---|---|---|
| Synthetisches Instrument | `/8.1_EQUIPMENT/GASI_TEST/GASI_TEST_INSTRUMENT_01` / `20261112143658368-19318` | [Instrument öffnen](https://playground.datastore.bam.de/openbis/webapp/eln-lims/?viewName=showViewSamplePageFromPermId&viewData=20261112143658368-19318) |
| Synthetischer Messlauf | `/8.1_PNEUMANN/GASI_TEST/GASI_TEST_RUN_01` / `20261112143750196-19319` | [Messlauf öffnen](https://playground.datastore.bam.de/openbis/webapp/eln-lims/?viewName=showViewSamplePageFromPermId&viewData=20261112143750196-19319) |
| RAW_DATA-Dataset | `20261112143835888-19320` | [Dataset öffnen](https://playground.datastore.bam.de/openbis/webapp/eln-lims/?viewName=showViewDataSetPageFromPermId&viewData=20261112143835888-19320) |

Das Instrument ist Parent des Messlaufs; der Messlauf ist Child. Das Dataset ist
am Messlauf registriert und gehört zur Laborbuch-Collection. Die Datei
`gasi_synthetic_test.csv` liegt im Dataset. Ein Objekt-Identifier enthält hier
Space, Projekt und Objektcode; der Collection-Pfad wird separat geführt.

## Live geprüft

- Beide Testprojekte und Collections angelegt, zurückgelesen und zentral konfiguriert.
- Auch die Einrichtung selbst live wiederholt: `created=[]`, keine weiteren Projekte oder Collections.
- Host, Typen, tatsächliche Pflichtfelder und Wertelisten erneut geprüft.
- Absichtlicher Abbruch nach gespeichertem Instrument; anschließend mit neuer
  Verbindung fortgesetzt. Instrument wiederverwendet, Messlauf und Dataset ergänzt.
- Vollständigen Schreibablauf mit neuer Verbindung wiederholt: alle IDs unverändert,
  alle drei `created`-Flags beim zweiten vollständigen Start `false`.
- Je genau ein Instrument, ein Messlauf und ein Dataset gezählt.
- Parent-Beziehung erneut gelesen; synthetische Datei zweimal heruntergeladen.
- SHA-256 von Original und beiden Downloads identisch:
  `5a92144d8bf41b6109398b5016018c36ab34262b0c7260c4dd2d594ca73be2b1`.

Der vollständige maschinenlesbare Befund liegt lokal unter
`.local_playground_test/live_verification.json`; die wiederholte Einrichtung unter
`.local_playground_test/provisioning_repeat.json`.

Beim Wiederholen wurde ein pyBIS-Fehler in der Objektiteration von
Property-Assignments belegt und korrigiert. Kataloge, Wertelisten und Assignments
werden als bereits geladene Tabellen gelesen; Objekt-/Dataset-Abfragen behalten
ihre pyBIS-Methoden. Das vermeidet zusätzliche Einzelabfragen und das fehlerhafte
Deepcopy eines bereits benutzten Clients. Der gezielte Regressionstest und die
anschließende Live-Wiederholung sind bestanden.

## Standort: ausdrücklich synthetischer Pflichtfeld-Testwert

`INSTRUMENT` verlangt einen Wert aus `BAM_LOCATION_COMPLETE`. Die Session darf
diese globale Werteliste nicht ergänzen; der Versuch wurde vom Server verweigert.
Es wurde kein neuer Standort angelegt. Für dieses fiktive Testinstrument wurde
stattdessen ein vorhandener gültiger Code ausschließlich als technischer Testwert
verwendet. Der konkrete Code steht in der lokalen Ziel-JSON.

`synthetic_location.not_a_physical_assignment=true` und die Beschreibung am
Instrument kennzeichnen: **keine reale Raumzuordnung, kein echtes Gerät**.
Dieser Ansatz dient nur dem synthetischen API-Test. Für echte Geräte müssen
Standort, Identität und Einbau fachlich belegt sein. Ein neuer neutraler
Standortwert würde eine Freigabe und technische Anlage durch die Instanzverwaltung
benötigen; dies ist für den bestandenen synthetischen Test nicht erforderlich.

## Wiederverwenden

Die Testziele sind bereits angelegt. Normaler Ablauf: Notebook 04 lesen, danach
Notebook 05 mit deaktiviertem Schreibschalter prüfen. Zum erneuten tatsächlichen
Schreibtest dessen letzte Zelle bewusst aktivieren. Die vorhandenen Einträge
werden wiederverwendet.

`GaSi_Playground_Testbereich_anlegen.ipynb` dient der einmaligen Einrichtung bzw.
Wiederaufnahme; Run All bleibt auch dort eine Vorschau. Der lokale Editor
`GaSi_Playground_Ziele_einrichten.ipynb` pflegt dieselbe Ziel-JSON. Echte Geräte und
Messdateien wurden nicht importiert; Sessionwerte und private Konfigurationen
bleiben außerhalb von Git.
