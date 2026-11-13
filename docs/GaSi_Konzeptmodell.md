# GaSi: vom Prüfauftrag zum nachvollziehbaren Ergebnis

Dieses Konzept folgt den vier Schritten der [BAM-Anleitung](https://datastore.bam.de/en/openbis_20-10-12/how-to_guides/user_ui/represent_research_data).
Es beschreibt den **aktuellen Aufbau und künftige Messläufe**. Es erzeugt keine
Einträge in openBIS. Geräteidentität, bestätigter Einbau und Eignung als Referenz
sind getrennte Aussagen.

**Aktueller Umsetzungsstand:** Messung sofort mit Originalen und Kontext erfassen;
Vorbereitung nur bei eigenständiger Freigabe/Wiederverwendung; Auswertung später
unabhängig ergänzen. [Projektstatus und aktuelle Instanzbefunde](GaSi_Projektstatus.md).
Das Erzeugen dieser Projektdokumentation schreibt nichts in openBIS.

## 1. Draw the research workflow

**Ein Gas- oder Gasfeuchtesensor wird definierten Prüfbedingungen ausgesetzt,
sein Signal wird aufgezeichnet und anschließend bewertet.** Der Sensor ist unser
Prüfobjekt („Sample“). GaSi stellt ihn nicht her.

```mermaid
flowchart TD
    %% gasi-view: workflow
    %% gasi-optional: P,E
    Q[Verfahren / Gültige SOP und Prüfauftrag] -->|wird verwendet| P[Vorbereitung / Optional eigenständiger Plan]
    P -->|legt fest| C[Belastungsprofil / Gas, Temperatur, Feuchte und Dauer]
    C -->|gibt Sollbedingungen vor| M[2. Beaufschlagen und messen / Sensorantwort und Referenzen erfassen]
    G[Gasquellen / Prüfgas und Trägergas] -->|werden verwendet| M
    D[Prüfobjekt: Sample / Gas- oder Gasfeuchtesensor] -->|wird geprüft| M
    I[GaSi und Referenzgeräte / MFC, Befeuchter und Messkette] -->|werden verwendet| M
    M -->|Messdaten sind Eingabe| E[Spätere Auswertung / Sensorsignal und Referenz vergleichen]
    W[Auswertesoftware / Festgehaltene Version] -->|wird verwendet| E
    P -->|erzeugt| DP[Prüfplan / Sollprofil und Startkonfiguration]
    M -->|erzeugt| DM[Messdaten / Logger-CSV und Lauf-Snapshot]
    E -->|erzeugt| DE[Prüfergebnis / Ergebnisdateien, Code und Bericht]
    classDef activity fill:#fff2cc,stroke:#d6b656,color:#172f3a
    classDef sample fill:#d5e8d4,stroke:#82b366,color:#172f3a
    classDef resource fill:#e1d5e7,stroke:#9673a6,color:#172f3a
    classDef dataset fill:#f8cecc,stroke:#b85450,color:#172f3a
    classDef conditions fill:#dae8fc,stroke:#6c8ebf,color:#172f3a
    class P,M,E activity
    class D sample
    class Q,G,I,W resource
    class DP,DM,DE dataset
    class C conditions
```

**Die Farben haben die Bedeutung der Vorlage:** Gelb = Tätigkeit, Grün = Prüfobjekt,
Lila = verwendete Ressourcen, Rot = Dateien/Datasets. Blau ergänzt bei GaSi das
Belastungsprofil. Grün behauptet keine Herstellung des Sensors durch GaSi.

**„Treatment Solution“ wird nicht wörtlich übernommen:** Gasquellen sind Materialien;
Temperatur und Feuchte sind Prüfbedingungen. Das Belastungsprofil enthält ihre
Sollwerte und die Stufendauer. Tatsächliche Bedingungen und Sensorantwort werden
getrennt gemessen. Beaufschlagung und Signalerfassung laufen im Messlauf gemeinsam;
es wird kein künstlicher zusätzlicher Behandlungsschritt pro Plateau erzeugt.

<details markdown="1">
<summary>Was gehört zu den drei Arbeitsschritten?</summary>

| Tätigkeit | Was geschieht bei GaSi? | Eigene Ergebnisse / Dateien |
|---|---|---|
| Vorbereiten | Prüfzweck und Prüfling festlegen; eingesetzte Geräte, Gasquellen, Kanal- und Messortzuordnung prüfen; Messstufen und Bezugsbedingungen festlegen. | Prüfplan, Sollprofil und geprüfte Startkonfiguration. Standard: direkt am Messlauf. Eigenes Objekt nur bei unabhängiger Freigabe oder laufübergreifender Wiederverwendung. |
| Beaufschlagen und messen | Den identifizierten Gas-/Gasfeuchtesensor dem Gas-, Temperatur- und Feuchteprofil aussetzen; Stufen durchlaufen; Sensorantwort, Referenz- und Prozesssignale gleichzeitig aufzeichnen. | Unveränderte Loggerdateien, tatsächlich verwendeter Lauf-Snapshot und gegebenenfalls Messprotokoll. |
| Auswerten | Gültige Zeitbereiche/Stufen auswählen; Soll, Referenz und Prüfling vergleichen; Korrekturen, Bedingungen und Unsicherheit dokumentieren. | Ergebnisdateien, Diagramme, Bericht sowie verwendeter Auswertecode mit Version. |

Ein Messlauf kann mehrere Dateien und Messstufen haben. Eine CSV-Zeile ist ein
Messpunkt, kein eigenes openBIS-Objekt. Wiederholte Auswertungen erhalten eigene
Auswertungsschritte und überschreiben weder Messdateien noch frühere Ergebnisse.

Die Gasmischung ist hier ein zeitabhängiger Prozesszustand im Lauf. Es wird kein
zusätzliches Probenobjekt für jedes Mischverhältnis oder Plateau erfunden. Ein
physisch entnommenes, weiterverwendetes Gas-/Materialmuster wäre ein neuer Fall.
Auch der Sensor nach der Beaufschlagung bleibt dasselbe physische Prüfobjekt.
Eine eigenständige Konditionierung, Alterung oder irreversible Behandlung wäre nur
dann ein zusätzlicher Arbeitsschritt, wenn sie tatsächlich stattfindet und eigene
dokumentierte Ergebnisse hat. Der vorliegende Aufbau belegt eine solche Trennung nicht.

| Angabe im Belastungsprofil | Sollwert | Tatsächlicher Wert / notwendiger Bezug |
|---|---|---|
| Gasgemisch | Komponente, Trägergas, nomineller Gehalt, Einheit und trocken/feucht-Bezug | Eine Rezeptkonzentration ist kein unabhängig gemessener Referenzwert. Gasquelle/Charge und gegebenenfalls Zertifikat referenzieren. |
| Temperatur T | Wert, Einheit und Zielort, z. B. Kammer oder Gas am Prüfling | Kammer-Ist, Gastemperatur und Sensortemperatur sind unterschiedliche Messgrößen. Zugeordneten Kanal und Messort nennen. |
| Feuchte H | Konkrete Größe: relative Feuchte, Tau-/Frostpunkt oder Stoffmengenanteil von Wasser; Wert und Einheit | Relative Feuchte braucht die zugehörige Gastemperatur; Tau-/Frostpunkt sind zu unterscheiden. Druck und Bezugszustand für die Umrechnung dokumentieren. |
| Druck und Durchfluss | Sollwert, Einheit; Druckart und Normalbedingungen, falls verwendet | Absolut-/Überdruck sowie Normvolumenstrom und Betriebsvolumenstrom unterscheiden. |
| Messstufe | Stufenkennung, Reihenfolge, Dauer und gegebenenfalls Wiederholung | Zeitbereich und Stabilitäts-/Auswahlregel; kein Objekt pro Messpunkt oder Stufe. |
| Sensorsignal | Kein Ersatz durch einen Soll- oder Referenzwert | Kanal, Sensorkennung, Einheit, Messort und Zeitbezug der tatsächlichen Antwort. |

Nicht geregelte Bedingungen werden ausdrücklich als solche dokumentiert. Ein
fehlender Feuchtewert darf nicht automatisch „trocken“ und eine fehlende
Temperaturzuordnung nicht „Sensortemperatur“ bedeuten.

Das Wiki, Abschnitt **1 Verfahrensprinzip**, belegt Prüfplan, Gasmischung,
Feuchteeinstellung und Signalerfassung. Die [Paper-SI](../data/paper/tg5c00105_si_001.pdf),
Abschnitt **1 Humidification unit**, belegt die methodische Trennung von Dosierung,
Befeuchtung und Referenzmessung; sie belegt keinen heutigen Einbau.
Der Logger und seine lokalen CSVs begründen die Trennung von Lauf, Stufe und Datei;
Feld- und Zeitregeln stehen im [detaillierten Datenmodell](GaSi_Datenmodell.md).

</details>

## 2. Identify Entities and Entity types

**Tätigkeiten:** Vorbereitung, Messung, Auswertung.<br>
**Prüfobjekt:** ein identifizierter Gas- oder Gasfeuchtesensor, vor und nach dem Lauf dieselbe Identität.<br>
**Verwendete Dinge:** Geräte, Gasquellen und versionierte Verfahren.<br>
**Ergebnisse:** Plan, Messdateien und Auswerteergebnisse.

### Vorbereitung: Objekte und Typen (nur falls eigenständig)

| Entitätstyp | GaSi-Objekte bzw. Dateien | Ort |
|---|---|---|
| `EXPERIMENTAL_STEP` | Vorbereitung: Prüfaufgabe und Messplan festlegen | Laborbuch |
| `SOP`, Kandidat | Verwendete, gültige Verfahrensversion | Vorhandenes BAM-/FB-Inventar; Ziel prüfen |
| `ATTACHMENT`, Dataset | Prüfplan, Stufensollprofil und Startkonfiguration | An der Vorbereitung |

### Messung: Objekte und Typen

| Entitätstyp | GaSi-Objekte bzw. Dateien | Ort |
|---|---|---|
| `EXPERIMENTAL_STEP` | Ein fachlich zusammenhängender GaSi-Messlauf | Laborbuch |
| `INSTRUMENT` | Verwendete MFC/MFM, Druckregler, Feuchtereferenzen und Erfassung | Geräteinventar; als Parents der Messung |
| Vorhandener Prüflingstyp | Gas- oder Gasfeuchtesensor („Sample“), mit seiner vorhandenen Identität | Passendes Inventar; als Parent der Messung |
| `GAS_BOTTLE`, Kandidat | Tatsächlich verwendete Gasquelle bzw. Flasche | Materialinventar; als Parent der Messung |
| `RAW_DATA`, Dataset | Unveränderte Loggerdateien | An der Messung |
| `ATTACHMENT`, Dataset | Tatsächlich verwendeter Prüfplan, Aufbau, Kanalplan und Messprotokoll | An der Messung |
| Kein eigenes Objekt erforderlich | Gas-/Temperatur-/Feuchteprofil mit Stufen, Dauer, Einheiten und Bezug | Standard: Sollprofil und tatsächlicher Kontext am Messlauf; eigenständiger Plan optional |

### Auswertung: Objekte und Typen

| Entitätstyp | GaSi-Objekte bzw. Dateien | Ort |
|---|---|---|
| `EXPERIMENTAL_STEP` | Auswertung eines oder mehrerer Messläufe | Laborbuch; verwendete Messungen sind Parents |
| `SOFTWARE_CODE`, Kandidat | Verwendete Version der Auswertesoftware | Vorhandenes BAM-/FB-Inventar; als Parent der Auswertung |
| `ATTACHMENT`, Dataset | Auswerteergebnisse, Diagramme, Bericht und reproduzierbarer Code | An der Auswertung |

Die Tabellen entsprechen der Sicht **Arbeitsschritt → Typen → konkrete Dinge**
im BAM-Beispiel. Sie zeigen GaSi-Kategorien; einzelne Seriennummern bleiben im
lokalen Gerätebericht. Dataset-Zeilen sind ausdrücklich Dateienablagen und keine
zusätzlichen Inventarobjekte. Spezialtypen für Ergebnisdaten sind unten aufgeführt.

<details markdown="1">
<summary>Entitäten, Typen und notwendige Angaben anzeigen</summary>

„Bestätigt“ meint den dokumentierten Playground-Abgleich vom 12.11.2026,
keine erneute Live-Prüfung bei dieser HTML-Erzeugung. „Katalog“ bestätigt nur
die Sichtbarkeit eines Typcodes; aktuelle zusätzliche Schema-Bestätigungen sind im Projektstatus getrennt aufgeführt. Schreibrechte bleiben offen.

| Fachliche Entität | openBIS-Ebene / Typ | Minimalangaben und Belegstand |
|---|---|---|
| Vorbereitung, Messlauf, Auswertung | Messung und spätere Auswertung je `EXPERIMENTAL_STEP`; Vorbereitung optional | Typ und Properties bestätigt. Fachlich: stabile Kennung, Zweck, Person, Beginn/Ende mit Zeitzone, verwendete Ressourcen. Die Messung braucht keine gleichzeitige Auswertung; Vorbereitung ist optional. |
| MFC, MFM, Druckregler, Feuchtereferenz, Erfassung, weitere einzeln verwaltete Geräte | Inventarobjekt `INSTRUMENT` | Bestätigt; Hersteller, Modell, Seriennummer als belegte Identität; OE und Standort. Rolle und Position gehören zur Verwendung im Aufbau. Ein MFC ist kein MFM. |
| Prüfling / DUT / fachliches „Sample“ | Der Gas-/Gasfeuchtesensor. Vorhandenes `INSTRUMENT` wiederverwenden, wenn er ein verwaltetes Gerät ist; sonst `TEST_OBJECT` oder geeigneter `SAMPLE`-Typ prüfen | SAMPLE- und TEST_OBJECT-Assignments sind jetzt lesend bestätigt; Pflichtfelder siehe Projektstatus. Das fachliche Wort Sample legt den API-Typ nicht fest. Kein zweites Sensorobjekt nach Beaufschlagung oder je Messstufe. |
| Gasquelle / Flasche / Referenzmaterial | `GAS_BOTTLE`, gegebenenfalls passender Materialtyp | Schema jetzt lesend bestätigt; Pflichtfelder SUPPLIER, GAS_VOLUME, GAS_PRESSURE_BAR und BAM_OE. Quelle/Charge, Zusammensetzung, Zertifikat und Gültigkeit bei Bedarf. Gasflasche, Betriebsmedium und dynamische Mischung unterscheiden. |
| Verfahrensvorschrift | `SOP` | Schema jetzt lesend bestätigt; konkrete gültige Version und die umfangreichen Pflichtfelder prüfen. Beim Vorbereiten referenzieren. |
| Softwareversion | `SOFTWARE_CODE` als wiederverwendbare Ressource | Schema jetzt lesend bestätigt; Pflichtfelder NAME und SOFTWARE_NAME. Loggerstand zusätzlich im Mess-Snapshot, Auswertecode bei der Auswertung sichern; keine ausführbaren Geheimnisse einbetten. |
| Aktueller Aufbau | Zunächst Setup-Datei; `SETUP.TEST` nur als späterer Objektkandidat | Typ bestätigt, aber keine Geräte-/Kanalproperties. Geräteposition, Messort, Signalrolle und Gasweg im Snapshot; kein künstliches Gerüst aus neuen Typen. |
| Belastungsprofil / Behandlung | Kein Flaschen-, Sensor- oder Geräteobjekt; versioniertes Sollprofil und tatsächliche Bedingungen als Dateien | Gaszusammensetzung, Temperatur, Feuchtegröße, Druck, Dauer; Soll, Referenz und Sensorsignal strikt trennen. `PARAMETER_SET` / `ENVIRONMENTAL_CONDITIONS` nur bei späterem belegtem Nutzen zusätzlich prüfen. |
| Anlagen- und Modulübersicht | Gliederung des Aufbaus | Noch keine eigenen Objekte nötig. Physische Teil-von-Beziehungen sind keine automatisch festgelegten Parent-Beziehungen. |
| Geräte-Kalibriernachweis | `CALIBRATION`, soweit Pflichtangaben belegt | Typ und Pflichtfelder bestätigt. Verweis `INSTRUMENT` hat API-Datentyp `SAMPLE`. Nicht mit dem GaSi-Prüflingstest gleichsetzen. |
| Plan, Snapshot, Messprotokoll, Bericht | Dataset `ATTACHMENT` an der erzeugenden Tätigkeit | Typ/Assignments bestätigt. Datensatz kann mehrere zusammengehörige Dateien enthalten. |
| Unveränderte Loggerdateien | Dataset `RAW_DATA` an der Messung | Typ bestätigt. „Unverändert“ bedeutet Loggerexport; dieser kann bereits Softwarekorrekturen enthalten. |
| Berechnete Daten / Auswertecode / Diagramme | An der Auswertung; zunächst `ATTACHMENT` möglich | `ANALYZED_DATA`, `SOURCE_CODE` und `FIGURE` sind Katalogkandidaten. Vor Nutzung Assignments prüfen. Kein neuer Typ erforderlich, um den Ablauf zu besprechen. |

Herstellerunterlagen sind vorhandene Ressourcenbelege, keine von GaSi erzeugten
Messdaten. Sie bleiben in diesem Projekt lokal. Dafür wird kein erfundener
Forschungsschritt angelegt.

Finanzielle Anlagen-Inventarnummer, physische Geräteidentität, Geräteposition und
openBIS-ID werden getrennt geführt. Die Registrierung einer Identität bestätigt
weder ihren aktuellen Einbau noch Kalibriergültigkeit.

</details>

## 3. Map the research workflow

**Laborbuch:** die Tätigkeiten und ihre Dateien.<br>
**Inventar:** wiederverwendbare Geräte und Materialien.

```mermaid
flowchart LR
    %% gasi-view: mapping
    LS[Laborbuch-Space / FB 8.1] -->|enthält| LP[Projekt / GASI]
    LP -->|enthält| LC[Collections / Vorbereitung, Messläufe, Auswertung]
    LC -->|enthält| LO[Objekte / EXPERIMENTAL_STEP]
    LO -->|Dateien zugeordnet| LD[Datasets / Plan, CSV, Ergebnis]
    IS[Inventar-Space / 8.1_EQUIPMENT] -->|enthält| IP[Projekt / GASI]
    IP -->|enthält| IC[Collection / INSTRUMENTS]
    IC -->|enthält| IO[Objekte / INSTRUMENT]
    GS[Materialinventar / Ziel noch offen] -->|enthält| GP[Projekt / Ziel noch offen]
    GP -->|enthält| GC[Collection / Gasquellen]
    GC -->|enthält| GO[Objekte / GAS_BOTTLE als Kandidat]
```

<details markdown="1">
<summary>Konkrete Ablage, Benennung und bestehende Ziele anzeigen</summary>

| Bereich | Geplante oder bestehende Ablage | Status |
|---|---|---|
| Dokumentierte Geräte | `/8.1_EQUIPMENT/GASI/INSTRUMENTS` | Bereits angelegt; zehn belegte Identitäten registriert. Kein Nachweis, dass alle aktuell eingebaut sind. |
| Echte Vorbereitung | `/<FB81_LAB>/GASI/PREPARATION` | Vorschlag, nicht angelegt; gemeinsames Laborbuchziel verbindlich auswählen. |
| Echte Messläufe | `/<FB81_LAB>/GASI/RUNS` | Vorschlag, nicht angelegt; keine Übernahme des persönlichen Testziels ohne Entscheidung. |
| Echte Auswertungen | `/<FB81_LAB>/GASI/ANALYSIS` | Vorschlag, nicht angelegt. Mehrere Auswertungen können dieselbe Messung verwenden. |
| Gasquellen | Freigegebenes BAM-/FB-Materialinventar, zunächst vorhandene Objekte suchen | Ziel und Pflichtfelder offen. Keine Space-/Collection-Codes erraten. |
| SOP / Software | Passendes bestehendes gemeinsames Inventar | Ablage und vorhandene Versionseinträge prüfen; keine Kopie pro Lauf. |
| Synthetischer Test | `/8.1_PNEUMANN/GASI_TEST/RUNS` und `/8.1_EQUIPMENT/GASI_TEST/INSTRUMENTS` | Bestehend und schreibend getestet; getrennt von echten Forschungsdaten. |

`<FB81_LAB>` ist ausdrücklich ein Platzhalter, kein ausführbarer Zielpfad.
Die bestehende Testfreigabe gilt nur für die konfigurierten Ziele; sie entscheidet
nicht über die Ablage echter Messläufe.

Eine Collection gruppiert Objekte; ihre Zugehörigkeit ist keine Parent-Beziehung.
Vorbereitung, Messung und Auswertung sind **Objekte**, keine Projects oder
Collections für einzelne Aufnahmen. Für einen anderen Prüfauftrag ist je nach
Umfang ein neues Projekt oder eine gemeinsame Projektgliederung möglich.

Anzeigenamen beispielsweise `GaSi – Messung – <Laufkennung>`; Codes sind davon
getrennte stabile Kennungen. Geräte behalten ihre Identität unabhängig von Position
und Bezeichnung. Eine Auswertung erhält eine eigene Kennung und referenziert die
unveränderten Eingabedatasets mit PermID und SHA-256.

</details>

## 4. Connect Entities

**Pfeile zwischen Objekten bedeuten Parent → Child.**
Die Dateien bleiben bei dem Arbeitsschritt, der sie erzeugt hat.

### Gesamtmodell: Laborbuch und Inventare

Wie im BAM-Beispiel sind **Space, Project, Collection, Object und Dataset**
gemeinsam dargestellt. Spalten und Ebenen zeigen die Ablage. Graue gestrichelte Linien ordnen Container/Objekte zu; blaue durchgezogene Objektpfeile zeigen Parents.
Rote punktierte Pfeile zeigen die Dataset-Zuordnung. Der tatsächliche Laufplan gehört standardmäßig zur Messung; der separate Prüfplan nur zur optionalen Vorbereitung.
Das Laborbuchziel und weitere
Ressourcenablagen sind Vorschläge beziehungsweise noch offen.

```mermaid
flowchart LR
    %% gasi-view: combined
    %% gasi-optional: P,E
    IS[8.1_EQUIPMENT / Geräteinventar] -->|enthält| IP[GASI / Bestehendes Projekt]
    IP -->|enthält| IC[INSTRUMENTS / Bestehende Collection]
    LS[FB-8.1-Laborbuch / Ziel noch offen] -->|enthält| LP[GASI / Projektvorschlag]
    LP -->|enthält| PC[PREPARATION / Vorschlag]
    LP -->|enthält| MC[RUNS / Vorschlag]
    LP -->|enthält| EC[ANALYSIS / Vorschlag]
    RS[BAM-/FB-Inventar / Weitere Ziele offen] -->|enthält| RP[Ressourcenprojekte / Ziele prüfen]
    RP -->|enthält| RC[Ressourcen / Gas, SOP, Software]
    Q[Verfahren / SOP als Kandidat] -->|Parent| P[Vorbereitung optional / EXPERIMENTAL_STEP]
    P -->|Parent| M[Beaufschlagung und Messung / EXPERIMENTAL_STEP]
    M -->|Parent| E[Auswertung später / EXPERIMENTAL_STEP]
    I[Verwendete Geräte / INSTRUMENT] -->|Parent| M
    G[Gasquelle / GAS_BOTTLE als Kandidat] -->|Parent| M
    D[Sensor-Prüfling / Vorhandene Objektidentität] -->|Parent| M
    W[Auswertesoftware / SOFTWARE_CODE als Kandidat] -->|Parent| E
    P -->|Dataset-Zuordnung| DP[Separater Prüfplan / ATTACHMENT, optional]
    M -->|Dataset-Zuordnung| DM[Rohdaten und Laufplan / RAW_DATA und ATTACHMENT]
    E -->|Dataset-Zuordnung| DE[Ergebnisse und Bericht / ATTACHMENT an Auswertung]
    IC -->|enthält| I[Verwendete Geräte / INSTRUMENT]
    PC -->|enthält| P[Vorbereitung optional / EXPERIMENTAL_STEP]
    MC -->|enthält| M[Beaufschlagung und Messung / EXPERIMENTAL_STEP]
    EC -->|enthält| E[Auswertung später / EXPERIMENTAL_STEP]
    RC -->|enthält| Q[Verfahren / SOP als Kandidat]
    classDef activity fill:#fff2cc,stroke:#d6b656,color:#172f3a
    classDef sample fill:#d5e8d4,stroke:#82b366,color:#172f3a
    classDef resource fill:#e1d5e7,stroke:#9673a6,color:#172f3a
    classDef dataset fill:#f8cecc,stroke:#b85450,color:#172f3a
    class P,M,E activity
    class D sample
    class I,Q,G,W resource
    class DP,DM,DE dataset
```

Ressourcenkästen stehen für einzelne wiederverwendbare Objekte. Bei einem
verwalteten Gerät als Prüfling wird seine bestehende Geräteidentität verwendet;
für andere Prüflinge bleibt Inventartyp und Ablage zu prüfen. Die rechte Spalte
fasst noch festzulegende Ressourcenablagen zusammen und behauptet keinen
gemeinsamen bereits existierenden Space.

<details markdown="1">
<summary>Nur die Objektbeziehungen groß anzeigen</summary>

```mermaid
flowchart LR
    %% gasi-view: relations
    %% gasi-optional: P,E
    Q[Verfahren / SOP als Kandidat] -->|Parent| P[Vorbereitung optional / EXPERIMENTAL_STEP]
    P -->|Parent| M[Beaufschlagung und Messung / EXPERIMENTAL_STEP]
    M -->|Parent| E[Auswertung später / EXPERIMENTAL_STEP]
    I[Verwendete Geräte / INSTRUMENT] -->|Parent| M
    G[Verwendete Gasquelle / GAS_BOTTLE als Kandidat] -->|Parent| M
    D[Sensor-Prüfling / Vorhandene Objektidentität] -->|Parent| M
    W[Auswertesoftware / SOFTWARE_CODE als Kandidat] -->|Parent| E
    classDef activity fill:#fff2cc,stroke:#d6b656,color:#172f3a
    classDef sample fill:#d5e8d4,stroke:#82b366,color:#172f3a
    classDef resource fill:#e1d5e7,stroke:#9673a6,color:#172f3a
    class P,M,E activity
    class D sample
    class Q,I,G,W resource
```

</details>

Die Kästen für Geräte und Gasquellen fassen mehrere mögliche Objekte zusammen.
Jedes tatsächlich verwendete Objekt wird einzeln verknüpft. Die Grafik zeigt
das Zielmodell; die einmalige Einrichtung testet Instrument → Messlauf samt Dataset synthetisch.

<details markdown="1">
<summary>Verbindungsregeln und Mehrfachverwendung anzeigen</summary>

| Verbindung | Umsetzung und Bedeutung |
|---|---|
| Vorbereitung → Messung → Auswertung | Parent-/Child-Verknüpfungen zwischen `EXPERIMENTAL_STEP`-Objekten: Voraussetzungen und Datenherkunft. Falls Vorbereitung keine eigenen Ergebnisse erzeugt, in die Messung integrieren. |
| Gerät / Referenz / Gasquelle / Prüfling → Messung | Ressourcen sind Parents des Laufs. Nur tatsächlich verwendete Identitäten auswählen. Rolle, Messort, Kanal und Einsatzzeit im Snapshot dokumentieren; eine Parent-Kante enthält diese Angaben nicht. |
| SOP → Vorbereitung; Softwareversion → Auswertung | Versionierte Ressourcen als Parents. Die Messsoftwareversion wird im Lauf-Snapshot festgehalten; ein eigener geprüfter Softwareeintrag kann zusätzlich Parent der Messung sein. |
| Mehrere Messungen → eine Auswertung | Alle verwendeten Messungen als Parents; die exakten Eingabedatasets und ausgewählten Bereiche zusätzlich im Auswertemanifest. Parent-Beziehung allein identifiziert keine Datei oder Messstufe. |
| Eine Messung → mehrere Auswertungen | Jedes eigenständig gespeicherte Ergebnis hat seinen erzeugenden Auswertungsschritt. Keine Rohdatenkopie als neues Messergebnis. |
| Tätigkeit → Dataset → Datei(en) | Dataset-Zuordnung, keine Parent-/Child-Beziehung. Ein Ergebnisbericht hängt an der Auswertung; ein während der Aufnahme erzeugtes Messprotokoll an der Messung. |
| Collection → Objekt | Ablagezugehörigkeit, keine Objektkante. |
| CALIBRATION → Gerät | Typisierter Objektverweis `INSTRUMENT`, keine Parent-Kante. Ein Verweis ist im Hierarchiegraphen nicht automatisch wie eine Parent-Kante sichtbar. |
| Anlage / Modul / Position → Gerät | Fachliche Gliederung und Zuordnung im Setup. Noch keine festgelegte openBIS-Relation; nicht als bestätigte Parent-Kante darstellen. |

Mehrere Parents und mehrere Children sind zulässig (N:N). Pfeile beschreiben hier
Datenherkunft beziehungsweise Ressourcennutzung, nicht Gasströmungsrichtung,
Kabelverlauf oder zeitliche Rückkopplung. Der physische Aufbauplan ist eine andere Sicht.

Die BAM-Anleitung empfiehlt verbundene Objekte. Bereits registrierte Geräte ohne
Messlauf bleiben vorerst ohne Nutzungskante; dafür keinen künstlichen Messlauf
erzeugen. Beim ersten echten Lauf werden die verwendeten Geräte verbunden.

</details>

<details markdown="1">
<summary>Was wurde korrigiert, was ist noch zu entscheiden?</summary>

| Punkt | Entscheidung / noch fehlende Information | Fundstelle |
|---|---|---|
| Auswerteergebnisse bisher direkt am Messlauf | Eigener Auswertungsschritt, wenn eigene Ergebnisse erzeugt werden. Ein bloßes Messprotokoll bleibt an der Messung. | BAM-Anleitung: **Core Concepts**, **1. Draw the research workflow**. |
| Hardwareübersicht als gesamter Forschungsablauf | Als ergänzende Aufbausicht behalten; Forschungsablauf separat aus Tätigkeiten und ihren Ergebnissen entwickeln. | BAM-Anleitung: Schritte **1–3**; Wiki: **1 Verfahrensprinzip**. |
| DUT pauschal als INSTRUMENT | Vorhandenes Geräteobjekt wiederverwenden oder Typ entsprechend Prüflingsart prüfen. | BAM-Anleitung: **2.2 Define Entity Types**; Katalogbefund `TEST_OBJECT` / `SAMPLE`. |
| Anlage, Module und Setup als zwingende neue Objekte | Zunächst Gliederung/Snapshot; eigene Objekte erst bei belegtem Nutzen und geeigneten Properties. | BAM-Anleitung: **Simplify your diagram**, **2.3 Reuse Existing BAM Object Types**; `SETUP.TEST`-Assignments. |
| Echte Laborbuchablage | Gemeinsam nutzbaren Space und Projektverantwortung auswählen; Vorschlags-Collections bestätigen. | Testbereich ist persönlich, nicht automatisch das Forschungsziel. |
| Prüfling, Gasflaschen, SOP und Software | Konkrete Identitäten/Versionen, vorhandene Einträge, Pflichtfelder und Rechte prüfen. Typkatalog reicht nicht. | Lokaler Playground-Befund; lesende Bestandsprüfung der Einrichtung. |
| Aktueller Einbau und Kanalplan | Vor Ort bestätigen, welches Gerät an welcher Position bzw. welchem Messort betrieben wird. Sieben Identitäten bleiben offen. | Lokaler Gerätebericht; Geräteabgleich der einmaligen Einrichtung. |
| Erster echter Lauf | Laufgrenze, Zeitbasis, Messplan, zulässige Eingabewerte und Auswerteziel gemeinsam festlegen. Einbauenachweis und Referenzstatus sind laufbezogen zu bestätigen. | Detailliertes Modell: Messlauf und Messwerte. |
| Parser | Erst nach verbindlicher Lauf-/Datei-/Kanalzuordnung spezifizieren; kein bereits vorhandener GaSi-Parser aus dem Katalog ableitbar. | BAM-Parserseite verlinkt Beispiele und eine ETL-Anleitung; sie liefert keine GaSi-Feldzuordnung. |
| Forschungsupload | Das Messdaten-Notebook erfasst die Messung; das optionale Auswertungsnotebook ergänzt später unabhängig Auswertungen mit echten Server-Eingabezeigern. Sensor und Ressourcen müssen existieren; fehlende Identitäten werden nicht erfunden. | [Uploadvertrag und offene Voraussetzungen](GaSi_Forschungsupload.md). |

**Stand:** Konzeptabgleich am 13.11.2026, offline gegen lokale Nachweise.
Der aktuelle lesende Zugang ist erfolgreich; die zusätzlichen Schemata sind
bestätigt. Das bisherige Laborbuch-Testziel ist jedoch derzeit nicht lesbar.
Native Dataset-Parents und die gemeinsame Originalablage bleiben bis zur
synthetischen Live-Abnahme schreibgesperrt. Keine echten Messdaten hochgeladen.
Details: [aktueller Projektstatus](GaSi_Projektstatus.md).

</details>

<details markdown="1">
<summary>Quellen und weiterführende Links</summary>

- [BAM: Conceptual Data Model, Schritte 1–4](https://datastore.bam.de/en/openbis_20-10-12/how-to_guides/user_ui/represent_research_data), gelesen am 13.11.2026.
- [BAM: EuVSOP](https://datastore.bam.de/en/use_cases/euvsop), Abschnitte **Register data in the Lab Notebook** und **Connect Inventory and ELN**: getrennte Tätigkeiten mit Datasets, Ressourcen als Parents. Als Strukturvorbild verwendet, ohne dessen Forschungsobjekte oder Sondertypen auf GaSi zu übertragen.
- Direkt abgeglichene Beispielgrafiken: [Objekte und Typen je Arbeitsschritt](https://datastore.bam.de/use_case_pics/20260728_use_case_euvsop_objects_and_object_types.svg) und [Gesamtmodell mit Hierarchie und Beziehungen](https://datastore.bam.de/use_case_pics/20260728_use_case_euvsop_data_model.svg). Die GaSi-Ansicht verwendet deren Darstellungsprinzip mit eigenen Tätigkeiten, Typen und Dateien.
- Vom Nutzer bereitgestellte `20260630_1_workflow.svg`, SHA-256 `1057c0031e8af41216ff3d1707dca964a173b7250c9a1789b8fab706507c896c`: Materialsynthese, Sample Treatment, Charakterisierung und Analyse sowie vier Farbkategorien. GaSi übernimmt die Farbbedeutung, verwendet aber einen vorhandenen Sensor und ein Gas-/Temperatur-/Feuchteprofil. Das Original bleibt lokal und unverändert.
- [BAM: Parsers](https://datastore.bam.de/en/parsers), Einstieg zu Beispielen, Workshop und ETL-Pipeline. Weitere Umsetzung nach Bestätigung der GaSi-Semantik.
- [GaSi-Wiki](../data/wiki/home.txt), **1 Verfahrensprinzip**, **Aufbau**.
- [GaSi-Paper, Supporting Information](../data/paper/tg5c00105_si_001.pdf), **1 Humidification unit**, insbesondere Figure S1 und Referenzmessung auf Seite 3.
- Betriebscode `logger/measurement_logger.py`, `communication/a5b.py` und `config/gas_flow_config.json`; nur lesend abgeglichener Betriebscode außerhalb dieses Repositorys.
- [Detailliertes Datenmodell](GaSi_Datenmodell.md) und [aktueller Projektstatus mit Instanzbefunden](GaSi_Projektstatus.md). Gerätebelege, konkrete Kanalzuordnungen und Seriennummern bleiben lokal.

</details>
