# Implementierungsplan: Robuste Linux-Desktop-Verknüpfungen in Toolbox

## 1. Dokumentstatus

- Status: vollständig umgesetzt, nachauditiert und abgenommen am 27.07.2026
- Zielplattform: Linux Mint 22.3 Cinnamon x86_64
- Releaseformat: Onefile-AppImage und Quellcodebetrieb
- Schwerpunkt:
  - verständliche Fehlerbehandlung für `.desktop`-Dateien
  - Dateidrop auf vorhandene Toolbox-Kacheln
  - korrekte Auflösung von `Name=` und `Icon=`
- Ergänzt den bestehenden Plan:
  `plans/linux-mint-22.3-onefile-appimage-plan.md`
- Referenzspezifikationen:
  - https://specifications.freedesktop.org/desktop-entry/latest-single/
  - https://specifications.freedesktop.org/icon-theme-spec/latest/
  - https://docs.gtk.org/gio/method.AppInfo.launch.html
  - https://doc.qt.io/qt-6/qicon.html

## 2. Ausgangslage

### 2.1 Aktuelles Startverhalten

Linux-Desktop-Dateien werden derzeit mit folgendem externen Aufruf gestartet:

```text
gio launch <desktop-datei>
```

Toolbox prüft dabei nur den Exitcode des `gio`-Prozesses. Ein Exitcode `0`
bedeutet lediglich, dass GIO den Startauftrag angenommen hat. Das gestartete
Zielprogramm kann danach trotzdem unmittelbar fehlschlagen. GIO dokumentiert
ausdrücklich, dass dieser nachgelagerte Fehler nicht über den ursprünglichen
Launch-Aufruf ermittelt werden kann.

Das führt aktuell zu folgendem Benutzererlebnis:

1. Die Kachel wird aktiviert.
2. GIO meldet einen erfolgreichen Startauftrag.
3. Das Zielprogramm beendet sich mit einem Fehler.
4. Toolbox zeigt dennoch „Launched“ an.
5. Für den Benutzer passiert scheinbar nichts.

### 2.2 Aktuelles Drop-Verhalten

Dateidrops werden nur auf folgenden Widgets angenommen:

- allgemeine Drop-Zone
- Canvas-Viewport
- Canvas-Oberfläche

Ein Drop fügt die abgelegten Dateien als neue Toolbox-Einträge hinzu. Einzelne
Tool-Kacheln sind keine Drop-Ziele. Deshalb können Desktop-Dateien mit
`%f`, `%F`, `%u` oder `%U` nicht als Drop-Aktionen verwendet werden.

### 2.3 Aktuelles Icon-Verhalten

Toolbox fragt für alle normalen Dateien ausschließlich `QFileIconProvider` ab.
Dieser Provider interpretiert `Icon=` innerhalb einer `.desktop`-Datei nicht.
Alle untersuchten Desktop-Dateien erhielten deshalb dasselbe generische
Dateityp-Icon.

Im AppImage-/PySide-Kontext wurde zusätzlich festgestellt:

- `QIcon.themeName()` ist leer.
- `QIcon.themeSearchPaths()` enthält nur `:/icons`.
- Systempfade wie `/usr/share/icons` und
  `$XDG_DATA_HOME/icons` werden nicht automatisch berücksichtigt.
- Die gewünschten Icons sind auf Linux Mint vorhanden und werden korrekt
  aufgelöst, sobald Theme-Name und Theme-Suchpfade gesetzt sind.

### 2.4 Reale Referenzfälle

Die Umsetzung muss mindestens folgende Desktop-Einträge korrekt behandeln:

| Referenzfall | Relevante Felder | Erwartetes Verhalten |
|---|---|---|
| `Custom.desktop` | `%k`, `Icon=preferences-system` | Start per Klick; Drop wird abgelehnt |
| `Desktop-Verknuepfung-erstellen.desktop` | `%k %U`, `Icon=insert-link` | mehrere Dateien, Ordner und URLs per Drop |
| `URL-als-Linux-Verknuepfung.desktop` | `%k %F`, `Icon=web-browser` | mehrere lokale `.url`-Dateien per Drop |
| `Bildschirme-Standby.desktop` | direkter `Exec`, `Icon=video-display` | schneller erfolgreicher Prozess |
| `Mint Volume Leveler.desktop` | direkter `Exec`, `Icon=mint-volume-leveler` | langlebige GUI-Anwendung |

Die Tests dürfen keine echten System-Tweaks ausführen und keine produktiven
Benutzerdateien verändern. Für automatisierte Tests werden harmlose temporäre
Nachbildungen dieser Desktop-Dateien verwendet.

## 3. Zielbild

Nach der Umsetzung gilt:

1. Toolbox liest Linux-Desktop-Dateien selbst und stellt deren Metadaten
   strukturiert bereit.
2. Standardmäßige `Type=Application`-Einträge werden ohne Shell und mit
   standardskonform aufgelösten Feldcodes gestartet.
3. Unmittelbare Startfehler und schnelle Prozessabbrüche werden verständlich
   angezeigt.
4. Dateien und URLs können direkt auf kompatible Toolbox-Kacheln gezogen werden.
5. `Icon=` wird über absolute Dateien oder das aktive Linux-Icon-Theme
   aufgelöst.
6. Neue Desktop-Kacheln erhalten den lokalisierten Desktop-Namen, ohne später
   manuell geänderte Titel zu überschreiben.
7. Drops auf den Canvas-Hintergrund fügen weiterhin neue Einträge hinzu.
8. Die bestehende Windows- und macOS-Logik bleibt unverändert.
9. Die AppImage bleibt eine einzelne ausführbare Datei und verwendet die
   System-Desktop- und Icon-Infrastruktur kontrolliert.

## 4. Umfang

### 4.1 Im Umfang

- Lesen und Validieren von `[Desktop Entry]`
- `Type=Application`
- Metadaten:
  - `Name`
  - lokalisierte `Name[...]`-Werte
  - `Icon`
  - `Exec`
  - `TryExec`
  - `Path`
  - `Terminal`
  - `DBusActivatable`
  - `MimeType`
  - `Hidden`
  - `NoDisplay`
- Feldcodes:
  - `%f`
  - `%F`
  - `%u`
  - `%U`
  - `%i`
  - `%c`
  - `%k`
  - `%%`
- Ignorieren der veralteten Feldcodes:
  - `%d`
  - `%D`
  - `%n`
  - `%N`
  - `%v`
  - `%m`
- Ablehnung unbekannter Feldcodes
- Überwachter Start normaler Desktop-Anwendungen
- GIO-Fallback für zunächst nicht direkt unterstützte Sonderfälle
- Dateidrop und URL-Drop auf Tool-Kacheln
- visuelle Drop-Rückmeldung
- Icon-Theme-Initialisierung auf Linux
- absolute, themenbasierte und Fallback-Icons
- Cache mit sicherer Invalidierung
- Unit-, UI-, Integrations- und AppImage-Tests
- Dokumentation und Changelog

### 4.2 Nicht im Umfang

- automatische Reparatur oder Umschreibung fremder `.desktop`-Dateien
- Installation oder Registrierung fremder Desktop-Dateien
- vollständige Implementierung aller Desktop-Actions-Untergruppen
- eigene D-Bus-Aktivierungsimplementierung
- eigener Terminal-Emulator
- Änderung der eigentlichen Zielprogramme
- automatische Änderung von `MimeType=` in Benutzerdateien
- Ausführung echter Custom-System-Tweaks in automatisierten Tests
- dauerhafte Speicherung aufgelöster Icon-Dateipfade im Toolbox-Profil
- allgemeines Kopieren oder Verschieben von Dateien per Drop
- Windows-`.lnk`-Drop-Semantik

## 5. Architekturentscheidungen

### 5.1 Eine gemeinsame Desktop-Entry-Schicht

Parser, Validierung, Feldcode-Auflösung, Drop-Fähigkeiten und Icon-Metadaten
dürfen nicht unabhängig voneinander implementiert werden. Alle Funktionen
verwenden dasselbe unveränderliche Metadatenobjekt.

Vorgeschlagene Struktur:

```text
app/services/
├── desktop_entries.py
├── desktop_entry_launch.py
└── linux_icon_theme.py
```

Mögliche Datenobjekte:

```text
DesktopEntryMetadata
├── source_path
├── entry_type
├── name
├── icon
├── exec_line
├── try_exec
├── working_directory
├── terminal
├── dbus_activatable
├── mime_types
├── hidden
└── no_display

DesktopLaunchInput
├── local_paths
└── urls

DesktopLaunchCommand
├── executable
├── arguments
├── working_directory
├── environment
└── launch_mode
```

### 5.2 Kein Shell-Start

Die Desktop-Entry-Schicht erzeugt immer ein Argumentarray. Sie darf weder
`shell=True` noch einen zusammengesetzten Shell-String verwenden.

Ein Desktop-Eintrag darf ausdrücklich selbst `bash -c` oder `sh -c` als
Programm festlegen. Das ist dann Inhalt der vom Benutzer hinzugefügten
Verknüpfung und wird als reguläres Argumentarray gestartet. Toolbox fügt
darüber hinaus keine Shell-Interpretation hinzu.

### 5.3 Standardspezifische statt allgemeiner Shell-Zerlegung

Die `Exec=`-Syntax ähnelt einer Shell-Befehlszeile, ist aber nicht vollständig
mit Shell- oder `shlex`-Regeln identisch. Eine reine Verwendung von
`shlex.split()` reicht deshalb nicht als Spezifikationsimplementierung.

Der Parser muss insbesondere beachten:

- Feldcodes werden erst nach dem Entfernen der Desktop-Entry-Quoting-Ebene
  expandiert.
- `%F`, `%U` und `%i` dürfen nur als eigenständiges Argument vorkommen.
- Datei-Feldcodes innerhalb zitierter Argumente sind ungültig.
- Ein unbekannter `%X`-Code macht die Befehlszeile ungültig.
- Ersetzungen mit Leerzeichen bleiben einzelne Argumente.
- Feldcodes werden nur einmal expandiert.
- Es wird keine Variablen-, Glob- oder Command-Substitution durchgeführt.

### 5.4 Direkter Start und GIO-Fallback

| Desktop-Eintrag | Startmodus |
|---|---|
| `Type=Application`, `Terminal=false`, `DBusActivatable=false` | direkt und überwacht |
| `DBusActivatable=true` | GIO-Fallback |
| `Terminal=true` | GIO-Fallback, bis Terminalstart separat spezifiziert ist |
| `Type=Link` | vorhandenen System-URL-Öffner verwenden |
| unbekannter oder ungültiger Typ | vor Start ablehnen |

Für den GIO-Fallback muss die UI klar unterscheiden:

- „Startauftrag wurde an das Desktop-System übergeben“
- „Programm wurde gestartet“

Nur beim direkt überwachten Start darf Toolbox einen tatsächlichen
Prozessstart bestätigen.

### 5.5 Asynchrone Prozessüberwachung

Der UI-Thread darf nie auf ein gestartetes Programm warten. Empfohlen ist ein
Qt-basierter Prozessmanager mit Signalen oder eine gleichwertige thread-sichere
Brücke.

Erforderliche Zustände:

```text
prepared
starting
started
finished_successfully
failed_to_start
finished_with_error
delegated_to_gio
```

Fehlerausgabe:

- `stderr` fortlaufend lesen, damit kein Pipe-Deadlock entsteht.
- Pro Prozess nur eine begrenzte Ringpuffergröße speichern.
- Zielwert: maximal 64 KiB.
- Steuerzeichen für die UI-Darstellung bereinigen.
- Pfade in Logmeldungen möglichst auf sichere Dateinamen reduzieren.
- Bei schnellem Fehler Exitcode und letzte relevante Zeilen anzeigen.
- Bei einem Fehler nach langer Laufzeit Statusmeldung und Logeintrag verwenden,
  statt unerwartet ein modales Fenster in den Vordergrund zu bringen.

### 5.6 Drop-Semantik

Ein Drop auf eine Kachel und ein Drop auf den Hintergrund sind zwei
unterschiedliche Aktionen:

```text
Drop auf Kachel
    -> Eingaben an diese Kachel übergeben

Drop auf freien Canvas-Bereich
    -> neue Toolbox-Einträge hinzufügen
```

Für Desktop-Dateien:

| Feldcode | Drop-Verhalten |
|---|---|
| `%f` | eine lokale Datei; Mehrfachdrop nach definierter Ein-Datei-Regel |
| `%F` | alle lokalen Dateien als einzelne Argumente |
| `%u` | eine URL oder lokale Datei |
| `%U` | alle URLs beziehungsweise lokalen Dateien |
| kein Datei-Feldcode | Drop ablehnen und erklären |

Festzulegende Mehrfachdrop-Regel für `%f` und `%u`:

- bevorzugt je abgelegtem Element einen eigenen Prozess starten
- bei mehr als einem Element vorab eine nichtmodale Statusmeldung anzeigen
- bei einem Fehler weitere Starts kontrolliert abbrechen oder zusammenfassen

Remote-URLs dürfen niemals stillschweigend in leere lokale Pfade umgewandelt
werden.

### 5.7 MIME-Regeln

`MimeType=` dient als unterstützende Validierung, darf aber nicht die einzige
Entscheidungsquelle sein.

- Fehlt `MimeType=`, entscheiden Feldcode und Lokalität.
- Bei eindeutig nicht passendem MIME-Typ wird der Drop mit einer Erklärung
  abgelehnt.
- `application/octet-stream` gilt als generischer lokaler Dateityp.
- Verzeichnisse werden als `inode/directory` erkannt.
- `.url`-Dateien werden zusätzlich anhand Endung und MIME-Datenbank geprüft.
- Eine fehlerhafte MIME-Deklaration darf nicht zu einem Absturz führen.

### 5.8 Icon-Auflösung

Priorität:

1. gültiger absoluter Pfad aus `Icon=`
2. gültiger relativer Pfad nur dann, wenn die Spezifikation und der konkrete
   Kontext ihn eindeutig erlauben
3. `QIcon.fromTheme(icon_name)`
4. `QFileIconProvider`
5. Toolbox-Standard-Icon

Linux-Theme-Suchpfade:

- `$XDG_DATA_HOME/icons`
- standardmäßig `~/.local/share/icons`
- jeder Eintrag aus `$XDG_DATA_DIRS` plus `/icons`
- standardmäßig `/usr/local/share/icons`
- `/usr/share/icons`
- `/usr/share/pixmaps` als Fallback-Suchpfad
- bestehendes Qt-Ressourcenpräfix `:/icons`

Theme-Ermittlung:

1. bereits von Qt erkanntes Theme
2. Cinnamon-Einstellung
   `org.cinnamon.desktop.interface icon-theme`
3. GNOME-Fallback
   `org.gnome.desktop.interface icon-theme`
4. `hicolor`

Ein fehlendes `gsettings` ist kein Startfehler der Anwendung.

### 5.9 Namen und bestehende Benutzerdaten

Beim erstmaligen Hinzufügen einer Desktop-Datei:

1. passenden lokalisierten `Name[...]`-Wert verwenden
2. danach `Name=`
3. danach Dateistamm

Bereits gespeicherte Toolbox-Titel dürfen nicht bei jedem Start überschrieben
werden. Dadurch bleiben vom Benutzer umbenannte Kacheln stabil.

Icons werden dynamisch aus der Zieldatei geladen und müssen nicht im
Profilformat gespeichert werden.

## 6. Geplante Dateien

### 6.1 Neue Dateien

```text
app/services/desktop_entries.py
app/services/desktop_entry_launch.py
app/services/linux_icon_theme.py
tests/test_desktop_entries.py
tests/test_desktop_entry_launch.py
tests/test_desktop_entry_drop.py
tests/test_linux_desktop_icons.py
tests/fixtures/desktop_entries/
```

### 6.2 Wahrscheinlich zu ändernde Dateien

```text
main.py
app/services/system_utils.py
app/services/paths.py
app/features/entries/controller_crud.py
app/features/entries/launching.py
app/features/tabs/controller.py
app/main_window.py
app/canvas/toolbox_canvas.py
app/canvas/surface_render.py
app/ui/widgets/canvas_widgets.py
app/ui/tabs/help_tab.py
tests/test_linux_launch.py
tests/test_linux_ui.py
tests/test_tab_management.py
tests/test_appimage_packaging.py
README.md
CHANGELOG.md
```

Die endgültige Dateiaufteilung darf während der Umsetzung angepasst werden,
solange Zuständigkeiten klar bleiben und keine zyklischen Imports entstehen.

## 7. Qualitäts- und Abnahmeregeln

Jeder Sprint ist erst abgeschlossen, wenn:

1. alle Sprinttests bestehen,
2. der vollständige bisherige Testbestand weiterhin besteht,
3. neue öffentliche Funktionen typisiert und dokumentiert sind,
4. keine echten Benutzer-Desktop-Dateien in Tests verändert werden,
5. keine Tests echte System-Tweaks oder Paketinstallationen starten,
6. die Oberfläche nicht blockiert,
7. Fehlermeldungen keine unbeschränkte Prozessausgabe enthalten,
8. Linux-spezifischer Code Windows und macOS nicht beeinflusst,
9. alle Prozessstarts ohne implizite Shell erfolgen,
10. AppImage-Tests mit bereinigter externer Prozessumgebung bestehen.

# Sprint 0: Baseline, Fixtures und verbindliche Verhaltensregeln

## Ziel

Eine reproduzierbare Ausgangslage schaffen und die erwartete Semantik vor der
Implementierung durch harmlose Fixtures festlegen.

## Aufgaben

1. Bestehende Tests vollständig ausführen und Ergebnis dokumentieren.
2. Temporäre Testfixtures für die fünf Referenzfälle erstellen.
3. Alle Fixture-Ziele als harmlose Hilfsprogramme ausführen:
   - Argumente in eine temporäre Datei schreiben
   - kontrolliert mit Exitcode `0` enden
   - kontrolliert mit Exitcode ungleich `0` enden
   - für GUI-Simulation bis zu einem Testsignal aktiv bleiben
4. Keine absoluten Benutzerpfade in Fixtures speichern.
5. Verbindliche UX-Texte festlegen:
   - ungültige Desktop-Datei
   - Zielprogramm fehlt
   - Verknüpfung akzeptiert keine Drops
   - nur lokale Dateien erlaubt
   - schneller Prozessfehler
   - Start an GIO delegiert
6. Mehrfachdrop-Regel für `%f` und `%u` verbindlich bestätigen.
7. Zeitgrenze für „schneller Startfehler“ festlegen.
   Empfohlener Ausgangswert: zwei Sekunden.
8. Obergrenze für gepufferte Fehlerausgabe festlegen.
   Empfohlener Ausgangswert: 64 KiB.

## Tests

### S0-T01: Vollständige Baseline

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

Erwartung: Der Ausgangsstand ist grün.

### S0-T02: Fixture-Isolation

Prüfen, dass alle Fixture-Ausgaben ausschließlich in einem temporären
Testverzeichnis landen.

### S0-T03: Keine produktiven Pfade

Testquellen nach `/home/jemi/Desktop` und anderen benutzerspezifischen
absoluten Pfaden durchsuchen. Solche Pfade sind in ausführbaren Tests verboten.

### S0-T04: Referenz-Desktop-Dateien

Alle Fixtures mit `desktop-file-validate` prüfen, sofern das Programm auf dem
Testsystem vorhanden ist.

### S0-T05: Plattformgrenzen

Linux-spezifische Tests werden auf anderen Plattformen sauber übersprungen,
nicht als Fehler ausgeführt.

## Abnahmekriterien

- Baseline dokumentiert.
- Fixtures sind sicher und reproduzierbar.
- UX- und Mehrfachdrop-Regeln sind entschieden.
- Noch kein Produktivverhalten wurde verändert.

# Sprint 1: Desktop-Entry-Parser und Metadatenmodell

## Ziel

Desktop-Dateien einmalig, sicher und spezifikationsnah lesen und validieren.

## Aufgaben

1. Unveränderliches `DesktopEntryMetadata`-Modell implementieren.
2. UTF-8-Dateien einschließlich optionaler BOM behandeln.
3. Nur die Gruppe `[Desktop Entry]` als Haupteintrag lesen.
4. Kommentare und leere Zeilen behandeln.
5. String-Escapes der Desktop-Entry-Spezifikation verarbeiten.
6. Lokalisierte Namen anhand aktueller Locale priorisieren.
7. Booleans streng und fehlertolerant normalisieren.
8. `MimeType`-Listen anhand des Semikolonformats lesen.
9. Dateigröße vor dem Lesen begrenzen.
   Empfohlener Höchstwert: 1 MiB.
10. Parserfehler in eine benutzergeeignete Fehlerklasse übersetzen.
11. Cache nach absolutem Pfad, Änderungszeit und Dateigröße aufbauen.
12. Cache-Invalidierung bei Dateiänderung und Dateilöschung sicherstellen.
13. Keine `%`-Interpolation einer allgemeinen Konfigurationsbibliothek
    zulassen.

## Tests

### S1-T01: Minimal gültiger Eintrag

`Type=Application`, `Name=` und `Exec=` werden korrekt gelesen.

### S1-T02: UTF-8 und Umlaute

Deutsche Namen wie „Desktop-Verknüpfung erstellen“ bleiben unverändert.

### S1-T03: Lokalisierter Name

Priorität von `Name[de_CH]`, `Name[de]` und `Name` prüfen.

### S1-T04: Prozentzeichen unverändert

`%k`, `%F`, `%U` und `%%` werden beim Einlesen nicht durch den
Konfigurationsparser verändert.

### S1-T05: Fehlende Gruppe

Eine Datei ohne `[Desktop Entry]` wird verständlich abgelehnt.

### S1-T06: Fehlendes Exec

`Type=Application` ohne `Exec=` und ohne D-Bus-Aktivierung wird abgelehnt.

### S1-T07: Ungültiger Typ

Unbekannte `Type=`-Werte werden nicht ausgeführt.

### S1-T08: Booleans

`Terminal`, `DBusActivatable`, `Hidden` und `NoDisplay` werden korrekt
normalisiert.

### S1-T09: MIME-Liste

Semikolonlisten, leere Elemente und fehlender Abschluss werden kontrolliert
behandelt.

### S1-T10: Dateigrößenlimit

Eine übergroße Desktop-Datei wird ohne hohen Speicherverbrauch abgelehnt.

### S1-T11: Cache-Invalidierung

Eine geänderte `Icon=`- oder `Exec=`-Zeile wird beim nächsten Zugriff erkannt.

### S1-T12: Defekte UTF-8-Daten

Fehlerhafte Kodierung erzeugt eine klare Diagnose statt eines ungefangenen
Unicode-Fehlers.

### S1-T13: Bestehende Referenzfälle

Harmlose Nachbildungen aller fünf Referenzfälle werden korrekt geparst.

## Abnahmekriterien

- Alle benötigten Metadaten stehen über eine zentrale API bereit.
- Parserfehler enthalten Dateiname und konkretes Problem.
- Der Parser führt keinerlei Programm aus.
- Alle S1-Tests und die vollständige Suite bestehen.

# Sprint 2: Feldcode-Auflösung und überwachte Fehlerbehandlung

## Ziel

Normale Desktop-Anwendungen sicher starten und nachgelagerte Startfehler in
Toolbox sichtbar machen.

## Aufgaben

1. Desktop-Entry-spezifischen `Exec=`-Tokenizer implementieren.
2. Erkannte Feldcodes exakt nach Spezifikation expandieren.
3. `%k` als lokalen Desktop-Dateipfad übergeben, wenn die Quelldatei lokal ist.
4. `%c` als lokalisierten Namen einsetzen.
5. `%i` als zwei Argumente `--icon` und Icon-Wert expandieren.
6. `%F` und `%U` in mehrere getrennte Argumente expandieren.
7. `%f` und `%u` nach der in Sprint 0 festgelegten Ein-Datei-Regel behandeln.
8. Datei-Feldcodes bei normalem Klick ohne Drop-Eingaben entfernen.
9. Veraltete Feldcodes entfernen.
10. Unbekannte Feldcodes ablehnen.
11. `TryExec` vor dem Start prüfen.
12. `Path=` als Arbeitsverzeichnis verwenden.
13. Nicht vorhandene Arbeitsverzeichnisse verständlich melden.
14. Umgebungsbereinigung aus `external_process_environment()` wiederverwenden.
15. Asynchronen Prozessmanager mit begrenztem `stderr`-Puffer integrieren.
16. Start-, Fehler- und Ende-Signale thread-sicher an die UI melden.
17. Bestehendes sofortiges „Launched“-Feedback durch echte Zustände ersetzen.
18. Schnellen Exitcode ungleich `0` mit Fehlerdetails anzeigen.
19. Erfolgreiche kurzlebige Helfer wie Standby nicht fälschlich als Fehler
    markieren.
20. Lang laufende GUI-Prozesse nicht blockierend verwalten.
21. GIO-Fallback für `Terminal=true` und `DBusActivatable=true` beibehalten.
22. Fallback-Status in UI und Log korrekt benennen.
23. Gleichzeitige Starts mehrerer Kacheln erlauben.
24. Prozessobjekte nach Ende zuverlässig freigeben.

## Tests

### S2-T01: `%k`-Expansion

Der Desktop-Dateipfad wird als genau ein Argument übergeben. Ein Pfad mit
Leerzeichen bleibt ein Argument.

### S2-T02: Problematischer Python-Wrapper

Eine harmlose Nachbildung des bisherigen
`python3 -c "...sys.argv[1]..." %k`-Starters erhält `sys.argv[1]` korrekt.

### S2-T03: `%F`

Mehrere lokale Dateien werden als getrennte Pfadargumente übergeben.

### S2-T04: `%U`

Lokale und entfernte URLs werden als getrennte URLargumente übergeben.

### S2-T05: `%f` und `%u`

Mehrfachdrops folgen exakt der in Sprint 0 festgelegten Startregel.

### S2-T06: `%i`

Mit vorhandenem Icon entstehen `--icon` und der Icon-Wert. Ohne Icon entstehen
keine zusätzlichen Argumente.

### S2-T07: `%c`

Der lokalisierte Desktop-Name wird als einzelnes Argument eingesetzt.

### S2-T08: `%%`

Ein doppeltes Prozentzeichen wird zu einem literalen Prozentzeichen.

### S2-T09: Veraltete Feldcodes

Alle spezifiziert veralteten Codes werden entfernt, nicht ausgeführt.

### S2-T10: Unbekannter Feldcode

`%x` oder ein anderer unbekannter Code verhindert den Start mit klarer Meldung.

### S2-T11: Ungültige Codeposition

`%F`, `%U` oder `%i` innerhalb eines anderen Arguments werden abgelehnt.

### S2-T12: Keine Shell-Injection

Argumente mit `$()`, Backticks, Semikolon, Pipes, Globs und Leerzeichen werden
literal weitergereicht.

### S2-T13: Fehlendes Ziel

Ein nicht auffindbares Programm wird vor beziehungsweise beim Start eindeutig
gemeldet.

### S2-T14: `TryExec`

Fehlendes oder nicht ausführbares `TryExec` verhindert den Start.

### S2-T15: Arbeitsverzeichnis

`Path=` und ein explizites Toolbox-Arbeitsverzeichnis werden nach festgelegter
Priorität behandelt.

### S2-T16: Schneller Python-Fehler

Ein Prozess mit Traceback und Exitcode `1` erzeugt eine sichtbare, begrenzte
Fehlermeldung.

### S2-T17: Großer stderr-Strom

Mehr als 64 KiB Ausgabe blockiert nicht und wird kontrolliert gekürzt.

### S2-T18: Erfolgreicher Kurzprozess

Ein schneller Exitcode `0` wird nicht als Fehler angezeigt.

### S2-T19: Lang laufender Prozess

Der UI-Thread bleibt responsiv, während der Testprozess aktiv ist.

### S2-T20: Gleichzeitige Prozesse

Zwei Starts werden separat verfolgt; Fehler und Ausgaben werden nicht
vermischt.

### S2-T21: GIO-Fallback

`Terminal=true` und `DBusActivatable=true` verwenden den delegierten Startpfad.

### S2-T22: AppImage-Umgebung

Externe Systemprogramme erhalten nicht den gebündelten AppImage-
`LD_LIBRARY_PATH`.

### S2-T23: Plattformregression

Windows- und macOS-Startpfade bleiben durch Mocks unverändert.

## Abnahmekriterien

- Die `%k`-Referenzfälle benötigen keine manuelle Reparatur mehr.
- Schnelle Prozessfehler werden sichtbar.
- Kein Start verwendet eine implizite Shell.
- Kein Prozess blockiert den UI-Thread.
- Alle S2-Tests und die vollständige Suite bestehen.

# Sprint 3: Dateidrop auf vorhandene Toolbox-Kacheln

## Ziel

Dateien, Ordner und URLs gezielt an kompatible Desktop-Kacheln übergeben.

## Aufgaben

1. `ToolTileWidget` als externes Drop-Ziel aktivieren.
2. Eigene Signale für Drag-Enter, Drag-Leave und Drop hinzufügen.
3. Entry-ID und unveränderte `QUrl`-Daten an den Controller übergeben.
4. Kacheln während eines gültigen Drops visuell hervorheben.
5. Ungültige Drops mit einer unterscheidbaren Darstellung markieren.
6. Drop-Hervorhebung bei Leave, Abbruch und Widget-Neuaufbau entfernen.
7. Drop auf ein Kind-Label zuverlässig an die Kachel weiterleiten.
8. Externen Dateidrag vom internen Kachelverschieben unterscheiden.
9. Desktop-Metadaten beim Drag-Enter verwenden, ohne Programme zu starten.
10. Kompatibilität anhand Feldcodes und Lokalität bestimmen.
11. Beim Drop einen `DesktopLaunchInput` erzeugen.
12. `%F` ausschließlich lokale Pfade übergeben.
13. `%U` URLs ohne Informationsverlust erhalten.
14. MIME-Prüfung und verständliche Ablehnung integrieren.
15. Drop auf Kacheln ohne Datei-Feldcode ablehnen.
16. Drop auf Hintergrund unverändert als „Eintrag hinzufügen“ behandeln.
17. Doppelte Ereignisverarbeitung verhindern.
18. Statusleiste und Fehlerdialoge konsistent verwenden.
19. Mehrfachdrop-Ergebnis zusammenfassen.
20. Nicht-Desktop-Kacheln zunächst nicht automatisch mit Argumenten starten,
    sofern dafür keine separate, dokumentierte Regel beschlossen wurde.

## Tests

### S3-T01: Drag-Enter auf `%F`-Kachel

Lokale Dateien werden akzeptiert und die Kachel zeigt einen gültigen Drop an.

### S3-T02: Remote-URL auf `%F`-Kachel

Der Drop wird abgelehnt; es wird kein leerer Pfad erzeugt.

### S3-T03: Drag-Enter auf `%U`-Kachel

Lokale Dateien, Verzeichnisse und entfernte URLs werden akzeptiert.

### S3-T04: Kachel ohne Datei-Feldcode

`Custom.desktop` akzeptiert keinen Dateidrop und startet nicht versehentlich.

### S3-T05: Drop auf Hintergrund

Die Datei wird weiterhin als neue Toolbox-Kachel hinzugefügt.

### S3-T06: Drop auf Kachel

Die Datei wird an die Ziel-Kachel übergeben und nicht als neuer Eintrag
gespeichert.

### S3-T07: Mehrere lokale Dateien

`%F` und `%U` erhalten alle Elemente in stabiler Reihenfolge.

### S3-T08: Dateinamen mit Leerzeichen und Unicode

Pfade bleiben unverändert und werden nicht zusammengefügt.

### S3-T09: Verzeichnisdrop

`inode/directory` wird für den `%U`-Referenzfall korrekt behandelt.

### S3-T10: `.url`-Datei

Der URL-Konverter erhält einen lokalen Pfad und nur kompatible Eingaben.

### S3-T11: MIME-Abweichung

Eine inkonsistente oder fehlende MIME-Angabe führt zu definiertem Verhalten,
nicht zu einem Absturz.

### S3-T12: Visueller Zustand

Gültig, ungültig, Leave und abgebrochener Drag setzen die korrekten
Widget-Eigenschaften.

### S3-T13: Interne Kachelbewegung

Das bestehende Halten-und-Verschieben funktioniert unverändert.

### S3-T14: Keine doppelte Verarbeitung

Ein Drop erzeugt genau einen Launch und keinen zusätzlichen Canvas-Eintrag.

### S3-T15: Widget-Neuaufbau

Nach Einstellungsänderung oder Canvas-Refresh funktionieren Drop-Signale weiter.

### S3-T16: Mehrfachauswahl

Die bestehende Mehrfachauswahl und das gemeinsame Verschieben bleiben
unverändert.

### S3-T17: Fehler im Zielprozess

Ein per Drop gestarteter Prozessfehler verwendet dieselbe Fehlerbehandlung wie
ein Klickstart.

## Abnahmekriterien

- Drop auf Kachel und Drop auf Hintergrund sind eindeutig getrennt.
- Die beiden Drop-Referenzstarter funktionieren mit temporären Testdaten.
- Interne Kachelbewegung und Mehrfachauswahl regressieren nicht.
- Alle S3-Tests und die vollständige Suite bestehen.

# Sprint 4: Desktop-Namen und korrekte Linux-Icons

## Ziel

Desktop-Kacheln mit ihrem vorgesehenen Namen und Icon darstellen.

## Aufgaben

1. Linux-Icon-Theme möglichst früh nach Erstellung der `QApplication`
   initialisieren.
2. XDG-Suchpfade ohne Duplikate und mit stabiler Reihenfolge aufbauen.
3. Aktives Cinnamon-Theme ermitteln.
4. GNOME- und `hicolor`-Fallback bereitstellen.
5. Fehler oder fehlendes `gsettings` still protokollieren und fortfahren.
6. `Icon=` aus dem gemeinsamen Desktop-Metadatenobjekt verwenden.
7. Absolute PNG-, SVG- und XPM-Pfade unterstützen.
8. Themenbasierte Namen mit `QIcon.fromTheme()` laden.
9. `QFileIconProvider` erst nach fehlgeschlagener Desktop-Icon-Auflösung
   verwenden.
10. Standard-Icon als letzte Stufe behalten.
11. Icon-Cache anhand Desktop-Datei und Theme-Konfiguration aufbauen.
12. Cache bei Änderung von `Icon=` invalidieren.
13. Cache bei Theme-Wechsel invalidieren oder neu aufbauen.
14. Bild- und Video-Thumbnail-Prioritäten unverändert lassen.
15. Neue Kacheln mit lokalisiertem `Name=` anlegen.
16. Bereits gespeicherte benutzerdefinierte Titel nicht überschreiben.
17. Optionalen Diagnose-Logeintrag für nicht auflösbare Icons hinzufügen.

## Tests

### S4-T01: Absolutes Icon

Eine gültige absolute PNG- oder SVG-Datei wird geladen.

### S4-T02: Fehlendes absolutes Icon

Ein nicht vorhandener Pfad fällt kontrolliert auf Theme beziehungsweise
Dateityp zurück.

### S4-T03: Themen-Icon

Ein temporäres Freedesktop-Testtheme liefert das in `Icon=` genannte Icon.

### S4-T04: XDG-Datenpfade

`XDG_DATA_HOME` und mehrere `XDG_DATA_DIRS` werden korrekt in Icon-Pfade
übersetzt.

### S4-T05: Cinnamon-Theme

Ein gemockter Cinnamon-Wert wird als Theme gesetzt.

### S4-T06: Fehlendes gsettings

Die Anwendung startet weiter und verwendet `hicolor`.

### S4-T07: Fallback-Kette

Theme, `QFileIconProvider` und Standard-Icon werden in richtiger Reihenfolge
verwendet.

### S4-T08: Fünf Referenzicons

`preferences-system`, `insert-link`, `web-browser`, `video-display` und
`mint-volume-leveler` werden im Linux-Mint-Integrationstest aufgelöst.

### S4-T09: Unterschiedliche Desktop-Icons

Mehrere `.desktop`-Dateien erhalten nicht mehr denselben generischen
Cache-Schlüssel beziehungsweise dieselbe gerenderte Testgrafik.

### S4-T10: Cache-Invalidierung

Eine Änderung von `Icon=alpha` zu `Icon=beta` wird ohne Neustart erkannt.

### S4-T11: Thumbnail-Regression

Bild- und Videovorschauen haben weiterhin Vorrang vor Dateityp-Icons.

### S4-T12: Lokalisierter Ersttitel

Eine neu hinzugefügte Desktop-Datei erhält den zur Locale passenden Namen.

### S4-T13: Persistierter Benutzertitel

Ein manuell geänderter gespeicherter Titel wird beim nächsten Start nicht
überschrieben.

### S4-T14: Skalierung

Icons bleiben bei minimaler, standardmäßiger und maximaler Kachelgröße scharf
und innerhalb der vorgesehenen Geometrie.

### S4-T15: AppImage-Systemicon

Ein Benutzericon aus `~/.local/share/icons/hicolor` wird aus der AppImage heraus
gefunden.

## Abnahmekriterien

- Alle Referenz-Desktop-Dateien zeigen ihr vorgesehenes Icon.
- Das Systemtheme wird verwendet, ohne fest auf Mint-Y-Sand codiert zu sein.
- Benutzerdefinierte Titel bleiben stabil.
- Alle S4-Tests und die vollständige Suite bestehen.

# Sprint 5: UI-Integration, Diagnose und Bedienbarkeit

## Ziel

Die neuen technischen Zustände verständlich und konsistent in die vorhandene
Toolbox-Oberfläche integrieren.

## Aufgaben

1. Startstatus erst nach tatsächlichem Prozessstart anzeigen.
2. GIO-Delegation sprachlich von überwachten Starts unterscheiden.
3. Fehlerdialog strukturieren:
   - Name der Verknüpfung
   - kurze Ursache
   - Exitcode, sofern vorhanden
   - gekürzte technische Details
4. Keine vollständigen sensiblen Argumentlisten standardmäßig anzeigen.
5. Technische Details optional kopierbar machen, falls dies ohne unnötige
   UI-Komplexität möglich ist.
6. Statusmeldungen für Drop-Ablehnung und Mehrfachstart ergänzen.
7. Tooltip oder Hilfetext für dropfähige Kacheln ergänzen.
8. Drop-Cursor und visuelle Zustände auf dem Mint-Y-Theme prüfen.
9. Kontextmenü und bestehende „Launch with Parameters“-Funktion abstimmen.
10. Benutzerdefinierte Launch-Argumente bei `.desktop` weiterhin nicht blind
    anhängen. Drop-Eingaben verwenden ausschließlich definierte Feldcodes.
11. Diagnose „Broken entries“ um Desktop-Entry-Validierung erweitern.
12. Hilfe-Tab aktualisieren.

## Tests

### S5-T01: Erfolgreicher Klickstart

Statusmeldung erscheint erst nach bestätigtem Prozessstart.

### S5-T02: Fehlgeschlagener Start

Eine klare Fehlermeldung ersetzt die irreführende Erfolgsmeldung.

### S5-T03: Delegierter GIO-Start

Die UI behauptet nicht, einen späteren Zielprozessfehler erkannt zu haben.

### S5-T04: Gekürzte Fehlerdetails

Sehr lange Ausgaben werden sichtbar als gekürzt markiert.

### S5-T05: Steuerzeichen

Terminal-Steuerzeichen beschädigen den Dialog nicht.

### S5-T06: Drop-Ablehnung

Eine nicht dropfähige Kachel erklärt, warum die Eingabe nicht angenommen wird.

### S5-T07: Drop-Erfolg

Die Statusleiste nennt Anzahl und Zielkachel.

### S5-T08: Broken-entries-Diagnose

Fehlendes `Exec`, `TryExec`, Icon und Zielprogramm werden differenziert
behandelt.

### S5-T09: Keine Argumentleckage

Logs und Standarddialoge enthalten keine unnötigen vollständigen
benutzerspezifischen Pfade oder sensible Argumentwerte.

### S5-T10: Tastaturbedienung

Klick-/Enter-Start funktioniert weiterhin; Drop-Unterstützung beeinträchtigt
Fokus und Auswahl nicht.

### S5-T11: Kontextmenü

Umbenennen, Entfernen, Öffnen des Speicherorts und Startoptionen bleiben
funktionsfähig.

### S5-T12: Hilfeinhalt

Der Hilfe-Tab beschreibt Kachel-Drop, Hintergrund-Drop und GIO-Grenzen korrekt.

## Abnahmekriterien

- Kein bekannter Startfehler wird fälschlich als sicherer Erfolg dargestellt.
- Benutzer können Drop-Fähigkeit und Ablehnungsgrund erkennen.
- Bestehende Bedienwege bleiben intakt.
- Alle S5-Tests und die vollständige Suite bestehen.

# Sprint 6: AppImage-, Linux-Mint- und Releaseabnahme

## Ziel

Die vollständige Funktion aus der Onefile-AppImage unter Linux Mint 22.3
validieren und releasefähig dokumentieren.

## Aufgaben

1. Vollständige Testsuite ausführen.
2. AppImage reproduzierbar neu bauen.
3. AppDir und AppImage separat testen.
4. Externe Prozessumgebung erneut prüfen.
5. Temporäres Test-Icon-Theme aus AppImage heraus auflösen.
6. Kachel-Drop unter echtem X11/Cinnamon testen.
7. Fünf Referenzfälle mit sicheren Testkopien prüfen.
8. Reale produktive Desktop-Dateien nur nach ausdrücklicher manueller
   Bestätigung starten.
9. Standby-Test nur mit automatischer DPMS-Rückholung ausführen.
10. Changelog und README aktualisieren.
11. Planstatus nach Umsetzung mit Testzahlen, Artefaktgröße und SHA-256
    aktualisieren.

## Automatisierte Tests

### S6-T01: Vollständige Unit- und UI-Suite

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q
```

### S6-T02: Releaseprüfung

```bash
./scripts/verify-linux-release.sh
```

### S6-T03: AppImage-Build

```bash
APPIMAGETOOL="$HOME/.local/bin/appimagetool" ./scripts/build-appimage.sh
```

### S6-T04: AppImage-Smoke-Test

```bash
./scripts/test-appimage.sh \
  dist-appimage/Toolbox-0.42-beta-x86_64.AppImage
```

### S6-T05: AppImage-Inhalt

Sicherstellen, dass keine Testfixtures, temporären Logs oder Benutzerdateien in
der AppImage enthalten sind.

### S6-T06: Desktop-Parser aus AppImage

Eine temporäre Desktop-Datei mit `%k` wird aus der AppImage heraus korrekt
gestartet.

### S6-T07: Drop-Argumente aus AppImage

Temporäre `%F`- und `%U`-Starter erhalten die erwarteten Argumente.

### S6-T08: Fehlerdiagnose aus AppImage

Ein absichtlich fehlschlagender temporärer Starter erzeugt einen sichtbaren
Fehler statt eines stillen Abbruchs.

### S6-T09: Icon-Auflösung aus AppImage

System-, Benutzer- und absolute Icons werden aus der isolierten Anwendung
aufgelöst.

### S6-T10: Schreibgeschützter Startort

AppImage aus einem nicht beschreibbaren Verzeichnis starten. Parser-, Icon- und
Drop-Funktionen dürfen nicht in das AppImage-Verzeichnis schreiben.

### S6-T11: Relokation

AppImage in einen Pfad mit Leerzeichen und Unicode verschieben und alle
Referenztests wiederholen.

### S6-T12: Extract-and-run

Die Funktion muss auch mit `--appimage-extract-and-run` bestehen.

## Manuelle Linux-Mint-Abnahme

### S6-M01: Richtige Icons

Alle fünf Referenzkacheln visuell vergleichen:

- Custom
- Desktop-Verknüpfung erstellen
- URL in Linux-Verknüpfung umwandeln
- Bildschirme in Standby
- Mint Volume Leveler

### S6-M02: Custom-Start

Nur das Fenster öffnen und ohne Anwendung eines Tweaks wieder schließen.

### S6-M03: Desktop-Verknüpfung per Drop

Eine temporäre Datei und einen temporären Ordner auf die Kachel ziehen.
Entstandene Verknüpfungen anschließend kontrolliert entfernen.

### S6-M04: URL-Konvertierung

Eine temporäre `.url`-Datei mit einer ungefährlichen HTTPS-Testadresse
verwenden und das erzeugte Desktop-Ziel validieren.

### S6-M05: Drop auf Hintergrund

Bestätigen, dass derselbe Drop auf freie Fläche weiterhin eine neue Kachel
hinzufügt.

### S6-M06: Schneller Fehler

Eine temporäre Desktop-Datei mit kontrolliertem Exitcode `7` starten und
Fehlermeldung prüfen.

### S6-M07: Fehlendes Ziel

Desktop-Datei mit nicht vorhandenem `TryExec` beziehungsweise `Exec` prüfen.

### S6-M08: Standby

Nur mit vorbereitetem automatischem `xset dpms force on` testen. Status muss
kurz `Off` und danach wieder `On` sein.

### S6-M09: Mint Volume Leveler

GUI starten, sichtbares Fenster bestätigen und sauber schließen.

### S6-M10: Theme-Wechsel

Zwischen zwei installierten Cinnamon-Icon-Themes wechseln, Toolbox neu starten
und korrekte Theme-Icons prüfen.

## Abnahmekriterien

- AppImage besteht sämtliche automatisierten Releaseprüfungen.
- Alle sicheren manuellen Mint-Tests sind dokumentiert.
- Keine Benutzerdatei wurde automatisch repariert oder überschrieben.
- SHA-256 und Artefaktgröße sind dokumentiert.
- README, Hilfe und Changelog entsprechen dem tatsächlichen Verhalten.

# 8. Gesamttestmatrix

| Ebene | Schwerpunkt | Automatisierung |
|---|---|---|
| Unit | Parser, Feldcodes, Icons, MIME | vollständig |
| Service | Prozessstart, Fehlerpuffer, GIO-Fallback | vollständig |
| Widget | Drag-Enter, Drop, Highlight | vollständig |
| Controller | Kachel- versus Hintergrunddrop | vollständig |
| Integration | harmlose Desktop-Fixtures | vollständig |
| AppDir | externe Umgebung, Theme-Pfade | vollständig |
| AppImage | Onefile-Start, Parser, Drop, Icon | weitgehend |
| Cinnamon/X11 | realer DnD und visuelle Darstellung | manuell |
| DPMS | Standby und Rückholung | manuell und abgesichert |

## P0 – releaseblockierend

1. Kein Shell-Injection-Pfad.
2. `%k`, `%F` und `%U` funktionieren.
3. Schnelle Prozessfehler werden angezeigt.
4. Drop auf Kachel erzeugt keinen zusätzlichen Toolbox-Eintrag.
5. Hintergrunddrop bleibt funktionsfähig.
6. Die fünf Referenzicons werden korrekt aufgelöst.
7. UI bleibt bei laufenden Prozessen responsiv.
8. AppImage-Start und Releaseprüfung bestehen.
9. Windows-Regressionstests bleiben grün.
10. Keine produktiven Benutzerdateien werden in Tests verändert.

## P1 – vor Freigabe erforderlich

1. Lokalisierte Namen.
2. MIME-Diagnosen.
3. Theme-Fallback ohne `gsettings`.
4. Cache-Invalidierung.
5. Mehrfachdrop und Unicode-Pfade.
6. Gekürzte und bereinigte Fehlerausgabe.
7. Dokumentation der GIO-Grenzen.

## P2 – sinnvolle Folgearbeiten

1. Desktop-Actions-Untergruppen.
2. Eigener kontrollierter Terminalstarter.
3. Drop-Unterstützung für normale ausführbare Dateien.
4. Kontextaktion „Desktop-Metadaten neu laden“.
5. Diagnoseansicht mit kopierbaren technischen Details.

# 9. Risiken und Gegenmaßnahmen

## Risiko 1: Unvollständiger Exec-Parser

Ein Shell-ähnlicher Parser kann Sonderfälle falsch behandeln.

Gegenmaßnahmen:

- Spezifikation als verbindliche Grundlage
- tabellengetriebene Feldcode-Tests
- keine allgemeine Shell-Auswertung
- unbekannte Syntax lieber ablehnen als erraten

## Risiko 2: Falsches Erfolgsversprechen beim GIO-Fallback

GIO kann nachgelagerte Startfehler nicht melden.

Gegenmaßnahmen:

- Fallback nur für definierte Sonderfälle
- UI-Text „an Desktop-System übergeben“
- Vorabvalidierung auch beim Fallback
- Einschränkung in Hilfe und Logs dokumentieren

## Risiko 3: UI-Blockade oder Pipe-Deadlock

Langlebige Programme oder große Fehlerausgaben können den Launcher blockieren.

Gegenmaßnahmen:

- asynchroner Prozessmanager
- fortlaufendes Lesen
- begrenzter Ringpuffer
- keine Warteoperation im UI-Thread

## Risiko 4: Drop-Konflikt mit Kachelbewegung

Externe Drops könnten als interne Bewegung interpretiert werden.

Gegenmaßnahmen:

- externe MIME-Drops getrennt behandeln
- bestehende Mausbewegungslogik nicht ersetzen
- explizite Regressionstests für Einfach- und Mehrfachbewegung

## Risiko 5: Unerwartete Programmausführung beim Drag-Enter

Eine reine Hover-Aktion darf nichts starten.

Gegenmaßnahmen:

- Drag-Enter führt nur Parser- und Kompatibilitätsprüfung aus
- Start ausschließlich im akzeptierten Drop-Event
- genau-einmal-Test

## Risiko 6: Theme ist nicht verfügbar

Minimalinstallationen besitzen weder Cinnamon-Theme noch `gsettings`.

Gegenmaßnahmen:

- `hicolor`-Fallback
- `QFileIconProvider`
- Standard-Icon
- Theme-Fehler nie als Anwendungsstartfehler behandeln

## Risiko 7: Benutzerdefinierte Titel gehen verloren

Ein automatisches Aktualisieren von `Name=` könnte gespeicherte Titel
überschreiben.

Gegenmaßnahmen:

- Desktop-Name nur beim erstmaligen Hinzufügen verwenden
- bestehendes Profilformat respektieren
- Persistenztest

## Risiko 8: Fremde Desktop-Dateien sind absichtlich gefährlich

Eine `.desktop`-Datei kann beliebige Programme starten.

Gegenmaßnahmen:

- bestehende Benutzeraktion „Kachel starten“ bleibt notwendige Autorisierung
- niemals beim Hinzufügen oder Hover starten
- keine automatische Reparatur
- keine Shell-Erweiterung durch Toolbox
- fehlende oder unbekannte Feldcodes streng ablehnen

## Risiko 9: AppImage-Bibliotheken beeinflussen Systemprogramme

Gebündelte Qt-/Python-Bibliotheken können externe Prozesse stören.

Gegenmaßnahmen:

- `external_process_environment()` für alle externen Starts
- AppImage-Integrationstest
- Systemprogramme nicht in den PyInstaller-Payload aufnehmen

# 10. Definition of Done

Die Umsetzung ist abgeschlossen, wenn:

1. alle Sprints vollständig abgenommen sind,
2. sämtliche P0- und P1-Tests bestehen,
3. die vollständige Testsuite grün ist,
4. die Onefile-AppImage auf Linux Mint 22.3 startet,
5. `%k`-Starter ohne manuelle Änderung funktionieren,
6. `%F`- und `%U`-Drops auf Kacheln funktionieren,
7. Drops auf freie Canvas-Flächen weiterhin Einträge hinzufügen,
8. schnelle Prozessfehler sichtbar sind,
9. GIO-Fallbacks ehrlich als delegierte Starts bezeichnet werden,
10. die fünf Referenzicons korrekt dargestellt werden,
11. benutzerdefinierte Kacheltitel erhalten bleiben,
12. keine produktive Desktop-Datei automatisch verändert wird,
13. keine neue Shell-Injection-Möglichkeit besteht,
14. README, Hilfe und Changelog aktualisiert sind,
15. Releaseartefakt, Dateigröße und SHA-256 dokumentiert sind,
16. der Planstatus auf „umgesetzt“ gesetzt und mit den finalen Testergebnissen
    ergänzt wurde.

# 11. Umsetzungs- und Abnahmenachweis

Die Sprints 0 bis 6 wurden am 27.07.2026 vollständig umgesetzt.

## Implementierte Kernfunktionen

- zentraler, größenbegrenzter Desktop-Entry-Parser mit Locale-, MIME- und
  Cache-Unterstützung
- sichere Feldcode-Auflösung für `%f`, `%F`, `%u`, `%U`, `%i`, `%c`, `%k`
  und `%%`
- kontrolliertes Entfernen veralteter Feldcodes und Ablehnung unbekannter Codes
- direkte Starts normaler `Type=Application`-Einträge ohne implizite Shell
- asynchrone Prozessüberwachung mit hart begrenztem 64-KiB-Ringpuffer im
  Arbeitsspeicher
- klar gekennzeichneter GIO-Fallback für Terminal- und D-Bus-Einträge
- vollständige Exec-, Feldcode- und Drop-Validierung vor jeder GIO-Delegation
- externe Datei- und URL-Drops direkt auf kompatible Kacheln
- weiterhin getrennte Hintergrund-Drops zum Hinzufügen neuer Toolbox-Einträge
- MIME- und Lokalitätsprüfung bereits während des Drag-Hovers und erneut beim
  Start von `%F`- und `%U`-Aktionen
- lokalisierte Namen beim erstmaligen Hinzufügen
- XDG-/Cinnamon-Icon-Theme-Initialisierung und Auswertung von `Icon=`
- absolute, themenbasierte und generische Icon-Fallbacks
- erweiterte Broken-Entry-Diagnose, Hilfe, README und Changelog
- Frozen-Smoke-Nachweis für Parser, `%F`-Drop-Expansion und Theme-Icon
- browserähnlicher `+`-Aktionsreiter mit `Ctrl+T` zum direkten Erstellen neuer
  Toolbox-Tabs

## Automatisierte Abnahme

- 211 Pytest-Tests bestanden
- `desktop-file-validate` und AppStream-Validierung bestanden
- AppDir-Smoke-Test bestanden
- normaler AppImage-Smoke-Test bestanden
- `--appimage-extract-and-run` bestanden
- Relokation, Symlink, Pfad mit Leerzeichen und schreibgeschützter Startort
  bestanden
- HiDPI- und echter X11/XCB-Test bestanden
- Frozen-Desktop-Fixture:
  - lokalisierter Name erkannt
  - `%F` erkannt
  - Drop-Pfad als separates Argument expandiert
  - Theme-Icon aufgelöst
  - direkter Startmodus vorbereitet
- ELF-, Inhalts-, Lizenz- und PyInstaller-Warnungsprüfungen bestanden
- finale Prüfung mit `scripts/verify-linux-release.sh` bestanden

## Sichere reale Referenzabnahme

- `Custom.desktop` mit unverändertem altem `%k`-Wrapper gestartet
- Fenster „Custom System Tweaks“ erkannt und ohne Anwendung eines Tweaks
  geschlossen
- `Desktop-Verknuepfung-erstellen.desktop` mit echtem `%U`-Drop in ein
  temporäres XDG-Desktop-Verzeichnis gestartet
- erzeugter symbolischer Link zeigte auf die erwartete temporäre Quelldatei
- `URL-als-Linux-Verknuepfung.desktop` mit echtem `%F`-Drop gestartet
- erzeugte Link-Datei bestand `desktop-file-validate`
- kein produktiver Benutzer-Desktop wurde bei diesen Drop-Tests verändert
- visuelle X11-Aufnahme aus der finalen AppImage bestätigte:
  - Monitor-Icon für „Bildschirme-Standby“
  - grünes Lautstärke-Icon für „Mint Volume Leveler“
  - keine generischen Zahnrad-Icons für diese beiden Einträge

## Nachaudit und geschlossene Restlücken

Der erneute vollständige Soll-Ist-Abgleich am 27.07.2026 fand vier
Abweichungen, die vor der erneuten Releaseabnahme geschlossen wurden:

1. `stderr` wurde für die Anzeige zwar auf 64 KiB gekürzt, während der
   Prozesslaufzeit aber noch vollständig in einer temporären Datei gehalten.
   Der Prozessmanager verwendet nun einen echten, fortlaufend geleerten
   64-KiB-Ringpuffer und kann dadurch weder Pipe-Deadlocks noch unbegrenztes
   Fehlerwachstum erzeugen.
2. Terminal- und D-Bus-Einträge wurden vor der GIO-Delegation noch nicht durch
   denselben Exec-, Feldcode-, MIME- und Drop-Validator geführt. Diese
   Vorabvalidierung ist jetzt verbindlich.
3. Die Drag-Hover-Farbe prüfte Feldcode und Lokalität, aber noch nicht die
   deklarierte MIME-Kompatibilität. MIME-Fehler werden nun bereits rot
   dargestellt und beim tatsächlichen Start nochmals validiert.
4. Der Drop-Controller überschrieb den korrekten GIO-Delegationsstatus mit
   einer allgemeinen „Launched“-Meldung. Der Abschlussstatus unterscheidet nun
   direkte Starts und Delegation und nennt Anzahl sowie Zielkachel.

Zusätzliche Tests decken Größenlimit, ungültiges UTF-8, alle veralteten
Feldcodes, leeres `%i`, explizite Arbeitsverzeichnis-Priorität,
Langläufer-Nichtblockierung, parallele Fehlerströme, harte
Ringpufferbegrenzung, ANSI-/Steuerzeichenbereinigung, GIO-Vorabvalidierung,
MIME-Hover, Icon-Cache-Invalidierung und differenzierte Diagnosen ab.

## Finales Releaseartefakt

`dist-appimage/Toolbox-0.42-beta-x86_64.AppImage`

- Größe: 60.773.568 Bytes
- Modus: ausführbar (`755`)
- SHA-256:
  `cb426ecc10f41c6dba08f9081461bda3f4c61dece5c1e546c6a929ce4a9df45d`
- Prüfsummendatei:
  `dist-appimage/Toolbox-0.42-beta-x86_64.AppImage.sha256`

Damit sind alle Punkte der Definition of Done erfüllt.
