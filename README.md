# GaSi: einrichten und Messdaten in openBIS erfassen

Im Hauptordner gibt es **drei Arbeitsnotebooks** und ein separates Notebook für den
Prüfling. Jedes startet mit einem frischen Kernel. Arbeitsverzeichnis ist dieses Repository.

| Reihenfolge | Notebook | Aufgabe |
|---|---|---|
| 1 · pro Session | [Session starten](GaSi_01_Session_starten.ipynb) | Token verdeckt eingeben/erneuern und den einzigen Schreibmodus setzen |
| 2 · einmalig | [Einmalig einrichten](GaSi_02_Einmalig_einrichten.ipynb) | Requirements installieren, Ziele konfigurieren, Collections und belegte Geräte einrichten, synthetischen Test prüfen; Modell/HTML erzeugen |
| 3 · pro Messlauf | [Messdaten hochladen](GaSi_03_Messdaten_hochladen.ipynb) | Originaldateien prüfen, Lauf und Ressourcen verknüpfen, hochladen und per Rückdownload/Hash verifizieren |
| Bei neuem Sensor | [Prüfling verwalten](GaSi_Pruefling_verwalten.ipynb) | Vorhandene Sensor-ID verwenden oder eine neue Identität registrieren und in die leere Laufvorlage übernehmen |

Die alten Einzelnotebooks sind zusammengeführt. Ihre lokalen Zustände einschließlich
ungespeicherter Git-Änderungen wurden unter
`.local_playground_test/notebooks_vor_vereinfachung_*/` gesichert. Alte Tabs schließen
und die oben verlinkten Dateien öffnen. Die Sicherungen bleiben außerhalb von Git.

## Ein einziger Schreibschalter

Nur in **Session starten**:

```python
SCHREIBEN = False
```

- `False`: Die Arbeitsnotebooks zeigen, was geschehen würde. Kein Schreiben in openBIS.
- `True`: Das jeweils ausgeführte Arbeitsnotebook schreibt in den BAM-Playground.

Die Zelle mit dem Schalter ausführen. Der Modus wird in der ignorierten `.env`
gespeichert und vor jedem Arbeitsaufruf erneut gelesen, auch in anderen Kernels.
Er bleibt bis zur nächsten Änderung in der Session bestehen. Zum Abschalten dieselbe
Zelle wieder mit `False` ausführen. Fehlende oder ungültige Einstellungen bedeuten Vorschau.
Es gibt keine weiteren Freigabeschalter und keine Confirmation-Strings.

Der Token wird über den Knopf **Token eingeben / erneuern** mit `getpass` abgefragt
und in derselben lokalen `.env` abgelegt. Er erscheint weder im Notebook noch im Git.
Ein vorhandenes `OPENBIS_PLAYGROUND_TOKEN` aus der Prozessumgebung hat beim Token Vorrang;
der Schreibmodus wird ausschließlich aus der lokalen `.env` gelesen.

Der Schalter steuert openBIS. Lokale Paketinstallation, Konfigurationsvorlagen,
Prüfberichte und HTML-Erzeugung funktionieren auch bei `False`.
Host, Zielpfade und fachliche Datenzuordnungen werden geprüft. Vor jedem Schreiben
werden Bestand, Typen und Pflichtfelder erneut aus der Instanz gelesen.
Der Schalter ändert keine serverseitigen Benutzerrechte.

## Erststart in VS Code

Python ab 3.10 und die Erweiterungen Python/Jupyter verwenden. Falls `.venv` fehlt:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install ipykernel
```

Oben rechts **Select Kernel → Python Environments → .venv** auswählen.
In **Einmalig einrichten** die Requirements-Zelle ausführen. Sie verwendet
`sys.executable -m pip install -r requirements-dev.txt` für genau diesen Kernel.
Danach bei neu installierten Paketen den Kernel neu starten. Conda und ein bestimmter
Umgebungsname sind nicht erforderlich. Anschließend Session starten und die
Einrichtung zunächst als Vorschau durchgehen; zum Ausführen den Sessionmodus ändern.

## Ziele und Geräte einmalig konfigurieren

Die zentrale Datei bleibt `config/playground_test_target.json`.
Der Editor in der Einrichtung speichert die expliziten Laborbuch- und Testinventarpfade.
Vorhandene Angaben werden übernommen. Aus diesen Projekten werden Messziel,
Auswertungscollection und `PRUEFLINGE` im GaSi-Inventar vorbereitet. Alle geplanten
Pfade werden angezeigt. Bestehende fremde Einträge werden nicht überschrieben.

Die Einrichtung umfasst die begrenzten `GASI_TEST`-Bereiche, das Geräteinventar
`/8.1_EQUIPMENT/GASI/INSTRUMENTS`, die Prüflingscollection und einen kleinen
synthetischen CSV-Test. Wiederholungen verwenden passende Einträge erneut.
Sie lädt keine echten Messdaten hoch. Serverseitige Schreibrechte und ein gültiger
Standortcode werden dabei tatsächlich geprüft.

Gerätebelege liegen lokal in `data/datasheets/`, der aktuelle Aufbau in
`config/gasi_setup.json`. Hersteller/Modell/Seriennummern werden gegen Belege geprüft.
Eine registrierte Geräteidentität bestätigt keinen aktuellen Einbau oder Kalibrierstatus.
Offene Identitäten und mehrdeutige Inventarnummern bleiben offen.

## Datenmodell und HTML neu erzeugen

In **Einmalig einrichten** unten die Zelle **Datenmodell und HTML neu erzeugen**
ausführen. Diese Zelle funktioniert einzeln mit frischem Kernel und ohne BAM-Zugang.
Nach einer Modelländerung genügt es, nur diese Zelle erneut auszuführen.

Erhalten bleiben die einfache und ausführliche Datenmodell-HTML sowie die farbige
Konzeptansicht mit Tabellen und vier SVGs. Quellen sind
[Datenmodell](docs/GaSi_Datenmodell.md) und [Konzeptmodell](docs/GaSi_Konzeptmodell.md).
Direkt öffnen: [einfache Übersicht](docs/GaSi_Datenmodell_einfach.html),
[farbiges Konzept](docs/GaSi_Konzeptmodell.html).

## Prüfling und Messlauf

Bei neuem Sensor `config/gasi_pruefling.json` ausfüllen und **Prüfling verwalten**
ausführen. Vorhandene `identifier` bevorzugen. Zur Neuanlage sind eine stabile
`local_id`, Name und die Pflichtfelder des gewählten Typs erforderlich. Ein vorhandener
Prüfling wird nicht nochmals angelegt. Bei bereits anderer Sensor-ID im Lauf bleibt
die Zuordnung erhalten, bis ein neuer Lauf ausdrücklich konfiguriert wird.

Für jede Messung steht in `config/gasi_run.json`: Laufkennung, Prüfling, tatsächlich
verwendete Geräte/Gase, Aufbau, Kanäle, Einheiten/Messorte, Stufen, Zeitbasis mit
UTC-Offset und ausgewählte Originaldateien/Records. Dann **Messdaten hochladen**
ausführen. Eine Auswertung ist dafür nicht erforderlich; der Plan liegt standardmäßig
am Messlauf. Fehlende fachliche Informationen werden nicht durch Beispieldaten ersetzt.

Originaldateien unter `data/measurements/` bleiben unverändert. Wiederholung und
Fortsetzung nach Teilfehlern verwenden stabile Kennungen. Gemeinsame Originaldateien
mehrerer Läufe bleiben bis zur Live-Abnahme ihrer Ablage gesperrt.
Siehe [Uploadbeschreibung und Browser-Abnahme](docs/GaSi_Forschungsupload.md).

Eine spätere Auswertung bleibt optional unter
[notebooks/GaSi_Auswertung_hochladen.ipynb](notebooks/GaSi_Auswertung_hochladen.ipynb).
Sie verwendet denselben Sessionmodus und präzise Eingabe-Dataset-IDs, Pfade, Hashes
und Auswahlbereiche; die Rohdaten werden nicht erneut hochgeladen.

## Prüfung und aktueller Stand

```powershell
.\.venv\Scripts\python -m unittest discover -s tests
.\.venv\Scripts\python tests/check_notebooks.py
```

Die Notebook-Prüfung startet isolierte frische Kernels mit gesperrtem Netzwerk.
Die Paketinstallation wird simuliert; Schreibabläufe verwenden synthetische Testclients.
Aktuell bestanden: **117 Unit-Tests**, fünf Notebooks in **14 frischen Kernels**;
31 Original-CSVs unverändert. Die neue gebündelte Einrichtung wurde lokal geprüft,
in diesem Schritt nicht live schreibend ausgeführt.
Prüfstand, Live-Befunde und noch fehlende Pilotangaben stehen im
[Projektstatus](docs/GaSi_Projektstatus.md).

Credentials, private Konfigurationen, Geräteunterlagen, Mess-/Ergebnisdateien und
lokale Prüfberichte bleiben von Git ausgeschlossen.
