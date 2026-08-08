# Sanierungsplan für die nach `f01cd7d` vorgenommenen Programmänderungen

## 1. Zweck und Ausgangslage

Dieser Plan beschreibt die vollständige technische Nacharbeit der Änderungen, die nach dem
Stand `f01cd7d` vorgenommen wurden. Er berücksichtigt sowohl die bereits committeten Änderungen
als auch den aktuell nicht committeten Arbeitsstand.

Die neuen Funktionen sind grundsätzlich sinnvoll, enthalten aber sicherheitskritische und
lebenszyklusbezogene Fehler. Deshalb gilt für die Umsetzung folgende Reihenfolge:

1. Unbeabsichtigte Ausführung fremder Dateien vollständig verhindern.
2. Abstürze, UI-Blockaden und unkontrollierte Hintergrundthreads beseitigen.
3. Fenster-, Tray- und Einzelinstanzverhalten konsistent machen.
4. Einstellungen, Dateizuordnungen und Ordner-Browse vollständig integrieren.
5. FFmpeg- und AppImage-Lieferkette reproduzierbar und überprüfbar machen.
6. Repository und Tests in einen verlässlich releasefähigen Zustand bringen.

Bis Sprint 3 abgeschlossen ist, sollte kein neues AppImage als stabiler Release veröffentlicht
werden. Die automatische Icon-Extraktion aus ausführbaren Dateien ist bis zum Abschluss von
Sprint 1 als Release-Blocker zu behandeln.

## 2. Übergreifende Qualitätsregeln

- Eine Datei darf niemals allein zur Metadaten- oder Icon-Ermittlung ausgeführt werden.
- Kein `wait()`, blockierendes `readline()` oder lang laufender Dateisystemzugriff darf auf dem
  GUI-Thread stattfinden.
- Hintergrundarbeiten werden zentral begrenzt, können veralten/abgebrochen werden und dürfen
  beim Schließen keine laufenden `QThread`-Kinder hinterlassen.
- Alle externen Linux-Prozesse verwenden die bestehende bereinigte Prozessumgebung aus
  `external_process_environment()`.
- Eine Einstellung gilt erst als fertig, wenn Laden, Anwenden, Speichern, JSON-Export,
  JSON-Import, Migration und Dirty-State getestet sind.
- Downloads von ausführbarem Code benötigen eine feste Version, eine erwartete SHA-256-Prüfsumme
  und ein fehlschließendes Fehlerverhalten.
- Tests müssen beobachtbares Verhalten prüfen. Reine Mock-Tests, die nur kontrollieren, ob eine
  Methode aufgerufen wurde, reichen für Lebenszyklus- und AppImage-Funktionen nicht aus.
- Jeder Sprint endet mit einem grünen Standardaufruf `pytest -q`; Sonderaufrufe nur für
  `tests/` sind nicht mehr ausreichend.

## 3. Sprintübersicht

| Sprint | Schwerpunkt | Priorität | Abhängigkeit |
|---|---|---:|---|
| 0 | Baseline, Testharness und reproduzierbarer Fehlernachweis | P0 | keine |
| 1 | Sichere Icon-Auflösung ohne Dateiausführung | P0 | Sprint 0 |
| 2 | Ordnerzähler und Tab-Größe: sichere Hintergrundarbeit | P0/P1 | Sprint 0 |
| 3 | Tray, Schließen, Beenden und Einzelinstanz | P1 | Sprint 2 |
| 4 | Einstellungen und Dateizuordnungen vollständig integrieren | P1 | Sprint 3 |
| 5 | Ordner-Browse funktional vervollständigen | P1/P2 | Sprint 2, 4 |
| 6 | FFmpeg-Download und AppImage-Lieferkette absichern | P1 | Sprint 1 |
| 7 | Repository-, Desktopdatei- und Testhygiene | P1/P2 | Sprint 1–6 |
| 8 | Linux-Mint-22.3- und AppImage-Releaseabnahme | P0-Abnahme | Sprint 1–7 |

---

## Sprint 0: Baseline und reproduzierbarer Fehlernachweis

### Ziel

Vor der Reparatur werden die vorhandenen Fehler als automatisierte Regressionstests erfasst.
Dadurch kann kein Fix später unbemerkt zurückfallen.

### Aufgaben

1. Den geprüften Ausgangsstand dokumentieren:
   - Git-HEAD, nicht committierte Dateien und verwendete Python-/Qt-Version erfassen.
   - Bekannte Umgebungsverschmutzung durch `LD_LIBRARY_PATH` getrennt vom Programmcode behandeln.
2. `pytest` zentral konfigurieren:
   - `testpaths = ["tests"]` setzen.
   - Einheitliche Qt-Testumgebung mit `QT_QPA_PLATFORM=offscreen` bereitstellen.
   - Eine gemeinsame `QApplication`-Fixture für GUI-Tests verwenden.
3. Für jeden kritischen Befund zunächst einen fehlschlagenden Regressionstest ergänzen:
   - Icon-Auflösung startet keine Zieldatei.
   - Schließen mit deaktiviertem Tray beendet die Anwendung.
   - Schließen mit aktiviertem Tray versteckt genau ein Fenster.
   - Canvas-Aktualisierung erzeugt keine unbegrenzte Anzahl Threads.
   - Speichern startet keine neue Größenberechnung während des Schließens.
   - Dateizuordnungen erhalten unter AppImage eine bereinigte Umgebung.
   - Tooltip- und Ordnerzähler-Einstellungen überstehen Speichern und Import.
4. Tests kategorisieren:
   - `unit`, `integration`, `gui`, `appimage`, `slow` als Marker registrieren.
   - Netzwerkzugriffe in der normalen Testsuite vollständig verbieten/mocken.

### Tests

- `env -u LD_LIBRARY_PATH QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest -q`
- `env -u LD_LIBRARY_PATH ./.venv/bin/python -m compileall -q app main.py tests`
- Test, dass während der Collection keine zweite `QApplication` erstellt wird.
- Test, dass kein Testmodul beim Import Dateien erzeugt oder `app.exec()` startet.

### Abnahmekriterien

- Jeder bekannte Fehler besitzt einen reproduzierbaren Test.
- Der normale Projekt-Testaufruf sammelt ausschließlich echte Tests ein.
- Die Baseline unterscheidet eindeutig zwischen Systemumgebungsfehlern und Programmfehlern.

---

## Sprint 1: Sichere Icon-Auflösung ohne Ausführung fremder Dateien

### Ziel

Icons werden ausschließlich über deklarative Metadaten, Sidecar-Dateien, Desktop-Themes oder den
Dateisystem-Iconprovider bestimmt. Die Zieldatei selbst wird dabei niemals gestartet.

### Betroffene Bereiche

- `app/services/linux_icon_theme.py`
- `app/canvas/surface_render.py`
- `tests/test_linux_desktop_icons.py`
- neuer Sicherheitstest, zum Beispiel `tests/test_icon_resolution_security.py`

### Aufgaben

1. `_extract_appimage_icon()` in der aktuellen Form entfernen.
2. Den Aufruf `subprocess.Popen([path, "--appimage-mount"])` vollständig entfernen.
3. Sichere Auflösungsreihenfolge definieren:
   1. Benutzerdefiniertes Icon aus dem Eintragsmodell.
   2. `Icon=` aus einer validen `.desktop`-Datei.
   3. Sidecar-Icon mit dokumentierter Namenskonvention.
   4. `QFileIconProvider` beziehungsweise Icon-Theme.
   5. Internes, stabiles Fallback-Icon.
4. Für AppImages zunächst bewusst das System-/Fallback-Icon verwenden, wenn keine sichere Quelle
   verfügbar ist. Eine spätere statische AppImage-Analyse darf nur mit einer geprüften
   Reader-Bibliothek erfolgen und niemals durch Starten des AppImages.
5. Cache-Schlüssel aus Pfad, Dateigröße und Änderungszeit bilden; negative Ergebnisse ebenfalls
   kurzzeitig cachen, damit ein fehlendes Icon nicht bei jedem Render erneut untersucht wird.
6. Breite `except Exception: pass`-Blöcke durch gezielte Fehlerbehandlung und Debug-Logging ersetzen.
7. Keine `sleep()`-, `readline()`- oder Prozess-Warteoperation in der synchronen Icon-Auflösung.

### Tests

1. **Nichtausführungstest:**
   - Temporäres ausführbares Shellscript anlegen, das beim Start eine Markerdatei erzeugen würde.
   - Icon auflösen.
   - Sicherstellen, dass keine Markerdatei existiert und `subprocess.Popen` nicht aufgerufen wurde.
2. **Hängertest:**
   - Eine ausführbare Testdatei verwenden, die nie Ausgabe erzeugen würde.
   - Icon-Auflösung muss innerhalb eines kleinen Zeitbudgets zurückkehren.
3. `.desktop` mit absolutem Iconpfad, Theme-Icon, fehlendem Icon und ungültigem Icon testen.
4. Sidecar-Dateien mit `.png`, `.svg`, Groß-/Kleinschreibung und fehlender Leseberechtigung testen.
5. Geänderte Quelldatei muss den Cache invalidieren.
6. Wiederholte Canvas-Aktualisierungen dürfen keinen Kindprozess erzeugen.

### Abnahmekriterien

- Kein Codepfad der Icon-Auflösung startet die Zielanwendung.
- Sicherheits- und Hängertests sind grün.
- Das korrekte Icon einer gültigen `.desktop`-Datei bleibt erhalten.

---

## Sprint 2: Sichere Hintergrundarbeit für Ordnerzähler und Tab-Größe

### Ziel

Dateisystemberechnungen bleiben reaktionsschnell, begrenzt und überleben Canvas-Aktualisierungen
oder das Schließen der Anwendung ohne Absturz.

### Teil A: Ordnerzähler

#### Aufgaben

1. `_FolderCountWorker` pro Tile entfernen.
2. Einen zentralen `FolderCountService` einführen:
   - Begrenzter Pool, zum Beispiel maximal zwei gleichzeitige Jobs.
   - Cache nach normalisiertem Pfad und Verzeichnis-Änderungszeit.
   - Generations-/Request-ID, damit verspätete Ergebnisse verworfen werden.
   - Keine Worker als Kind kurzlebiger Tile-Widgets.
3. Die Bedeutung des Zählers eindeutig festlegen und dokumentieren. Empfohlen wird die Anzahl der
   direkt enthaltenen, sichtbaren Elemente statt eines rekursiven Vollscans.
4. Fehlerzustände unterscheiden:
   - `…` während der Berechnung.
   - `–` oder Tooltip-Hinweis bei fehlenden Rechten/verschwundenem Ordner.
   - Kein irreführendes Teilergebnis als exakte Zahl anzeigen.
5. Suche, Auswahl und reine Style-Änderungen dürfen keinen neuen Zählauftrag erzeugen.
6. Beim Entfernen eines Tabs oder beim Programmende ausstehende Anfragen entkoppeln/abbrechen.

#### Tests

- 100 Ordnertiles erzeugen; Zahl gleichzeitiger Jobs bleibt am konfigurierten Limit.
- Canvas zehnmal neu rendern; keine zehnfachen Jobs für denselben Pfad.
- Widget vor Fertigstellung entfernen; kein Signalzugriff auf zerstörtes QObject.
- Berechtigungsfehler, gelöschter Ordner, Symlink-Schleife und sehr großer Ordner.
- Cache-Hit und Cache-Invalidierung nach Änderung des Ordners.
- Anwendung sofort nach Start schließen; kein `QThread: Destroyed while thread is still running`.

### Teil B: Tab-Gesamtgröße

#### Aufgaben

1. `wait()` aus `_recalculate_active_tab_size()` entfernen.
2. Größenberechnung von `persist_toolbox_state()` entkoppeln.
3. Berechnungen nur bei relevanten Änderungen oder Tabwechsel starten und mit `QTimer` entprellen.
4. Der Worker erhält einen unveränderlichen Snapshot normalisierter Pfade statt der veränderbaren
   `ctx.entries`-Liste.
5. Pro Fenster maximal eine aktive Größenberechnung; alte Ergebnisse über Request-ID verwerfen.
6. Beim Schließen:
   - Keine neue Berechnung starten.
   - Abbruch anfordern.
   - Keine unbeschränkte Warteoperation im GUI-Thread.
7. Doppelte und ineinander verschachtelte Pfade deduplizieren, damit Größen nicht doppelt gezählt
   werden.
8. Ergebniszustände explizit darstellen: exakt, geschätzt, abgebrochen oder nicht verfügbar.

#### Tests

- Eine langsame Berechnung simulieren; ein GUI-Timer muss währenddessen weiterlaufen.
- Mehrere schnelle Persist-/Tabwechsel erzeugen höchstens eine aktuelle Berechnung.
- Ergebnis eines alten Tabs darf die Statusanzeige des neuen Tabs nicht überschreiben.
- Schließen während der Berechnung beendet sauber.
- Doppelte Datei und Eltern-/Unterordner-Kombination werden nicht doppelt gezählt.
- Nicht lesbarer Pfad, Symlink, Socket, gelöschte Datei und Timeout.
- Formatierung für Byte, KiB, MiB, GiB und geschätztes Ergebnis.

### Abnahmekriterien

- Kein GUI-Code verwendet `QThread.wait()` für diese Funktionen.
- Die Anzahl paralleler Dateisystemjobs ist begrenzt.
- Suche und Canvas-Reflow bleiben bei vielen Ordnern flüssig.
- Alle Shutdown-Tests laufen ohne Qt-Threadwarnung oder Prozessabbruch.

---

## Sprint 3: Tray, Schließen, Beenden und Einzelinstanz

### Ziel

Schließen, Verstecken, Wiederherstellen und Beenden besitzen eindeutige, testbare Semantik. Mehrere
Fenster dürfen keine Konfigurationsdaten überschreiben.

### Teil A: Tray-Lebenszyklus

#### Aufgaben

1. Die doppelten `closeEvent()`-Definitionen zu genau einer Methode zusammenführen.
2. Gewünschtes Verhalten festlegen:
   - Tray deaktiviert: Schließen beendet das letzte Fenster und die Anwendung.
   - Tray aktiviert und verfügbar: Schließen versteckt das Fenster.
   - Tray aktiviert, aber nicht verfügbar: normales Beenden mit verständlichem Fallback.
3. Einen expliziten `_force_quit`-Pfad für „Beenden“ im Tray-Menü einführen.
4. `setQuitOnLastWindowClosed()` abhängig vom wirksam angewendeten Tray-Modus setzen, nicht
   pauschal auf `False`.
5. Tray-Icon und Tray-Menü einmal pro Anwendung statt einmal pro Fenster besitzen.
6. Vor Beenden alle Manager genau einmal herunterfahren und Zustand genau einmal speichern.

#### Tests

- Tray aus: `close()` akzeptiert das Event und beendet die Anwendung.
- Tray an: `close()` ignoriert das Event, versteckt das Fenster und hält die Anwendung aktiv.
- „Beenden“ im Tray: trotz aktiviertem Tray vollständiges Ende.
- Kein verfügbarer System-Tray: kein Zugriff auf ein nicht vorhandenes `tray_icon`.
- Mehrfaches Schließen/Öffnen erzeugt weder weitere Icons noch weitere Signalverbindungen.

### Teil B: Einzelinstanz und Fensterstrategie

#### Aufgaben

1. Bis ein gemeinsamer State-Controller existiert, einen zweiten Start standardmäßig als
   `ACTIVATE_EXISTING` behandeln, nicht als `NEW_WINDOW`.
2. Falls echte Mehrfensterunterstützung gewünscht bleibt, diese separat entwerfen:
   - Ein gemeinsames In-Memory-Modell pro Prozess.
   - Zentral serialisierte Schreibvorgänge.
   - Konfliktfreie Fenster- und Tab-Ownership.
3. Einzelinstanzserver in einen `ApplicationController` auslagern.
4. Stale Sockets nur nach sicherem Retry entfernen; niemals einen möglicherweise aktiven Server
   pauschal löschen.
5. IPC-Callbacks nicht mit blockierendem `waitForReadyRead()` im GUI-Thread implementieren.
6. Smoke-Test-Modus vor der normalen Einzelinstanzweiterleitung behandeln oder einen eindeutigen,
   testisolierten Servernamen verwenden.
7. Servername aus stabiler App-ID und Benutzerkontext ableiten; Testinstanzen müssen isolierbar
   sein.

#### Tests

- Zwei Prozesse starten: der zweite aktiviert das erste Fenster und beendet sich erfolgreich.
- Zwei nahezu gleichzeitig gestartete Prozesse erzeugen genau einen Server.
- Staler Socket wird sicher erkannt und wiederhergestellt.
- Ein laufendes normales Toolbox-Fenster verhindert keinen AppImage-Smoke-Test und übernimmt
  dessen Testkonfiguration nicht.
- Änderungen aus einem Fenster können nicht durch einen veralteten zweiten Zustand überschrieben
  werden.

### Abnahmekriterien

- Genau eine wirksame `closeEvent()`-Methode.
- Tray-Modus entspricht in allen drei Zuständen der Einstellung.
- Einzelinstanz- und Smoke-Tests sind deterministisch grün.

---

## Sprint 4: Einstellungen und Dateizuordnungen vollständig integrieren

### Ziel

Neue Einstellungen werden konsistent angewendet und Dateizuordnungen funktionieren auch im
AppImage mit denselben Sicherheits- und Fehlerregeln wie bestehende Starts.

### Teil A: Einstellungsschema und Roundtrip

#### Aufgaben

1. Ein zentrales Einstellungsschema beziehungsweise eine deklarative Key-Liste einführen, damit
   dieselben Keys für Laden, Speichern, Snapshot und Import verwendet werden.
2. Folgende derzeit unvollständige Keys schließen:
   - `interaction/show_tooltips`
   - `system/folder_show_file_count`
   - alle `system/file_assoc_*`-Felder
3. Für jeden Key unterstützen:
   - Defaultwert.
   - Laden aus `QSettings`.
   - Pending-/Applied-State.
   - Dirty-State.
   - Speichern nach `QSettings`.
   - JSON-Export und JSON-Import.
   - Rückwärtskompatible Migration bei fehlendem Key.
4. Tooltip-Default bewusst festlegen. Da Tooltips zuvor sichtbar waren, sollte ein Upgrade ohne
   gespeicherten Key das bisherige Verhalten erhalten oder eine dokumentierte Migration besitzen.
5. Alle neuen LineEdits, Checkboxen und Comboboxen mit `_mark_settings_dirty()` verbinden.
6. „Save & Apply“ nur dann deaktivieren, wenn Widgets und Applied-State tatsächlich gleich sind.

#### Tests

- Parametrisierter Roundtriptest für jeden Einstellungsschlüssel.
- Echte temporäre `QSettings` verwenden, nicht nur einen Snapshot-Mock.
- Export -> Defaults ändern -> Import -> alle Werte entsprechen wieder dem Export.
- Altes Profil ohne neue Keys importieren; dokumentierte Defaults werden verwendet.
- Änderung jedes Dateizuordnungsfeldes aktiviert „Save & Apply“.
- Neustarttest für Tooltip-, Ordnerzähler- und Dateizuordnungseinstellungen.

### Teil B: Dateizuordnungen und Prozessstart

#### Aufgaben

1. `file_associations.py` mit den bestehenden Startdiensten zusammenführen statt einen zweiten,
   abweichenden Prozesspfad zu pflegen.
2. Auf Linux `xdg-open`/`gio` über den vorhandenen Resolver und immer mit
   `external_process_environment()` starten.
3. Kein `shell=True`; Custom-App-Eingaben weiterhin mit `shlex.split()` zerlegen.
4. Konfiguriertes Programm vor dem Start validieren und einen verständlichen Fehler anzeigen,
   statt still auf ein anderes Programm auszuweichen.
5. Verhalten bei gespeicherten Tile-Startoptionen festlegen:
   - Besitzt ein Eintrag eigene Argumente/Arbeitsverzeichnis/Wait-Optionen, haben diese Vorrang.
   - Dateizuordnung gilt nur für den normalen Dokument-/Medienstart ohne spezielle Tile-Optionen.
6. Prozessstart als erfolgreich melden, wenn `Popen` wirklich erstellt wurde; Fehler nicht als
   „Launched“ anzeigen.
7. Benutzerdefinierte Flatpak-Kommandos und Pfade mit Leerzeichen unterstützen, ohne Shellsyntax
   zuzulassen.

#### Tests

- Linux-AppImage-Umgebung mit künstlichem `LD_LIBRARY_PATH` und `LD_LIBRARY_PATH_ORIG`.
- `xdg-open`, `gio`, direktes Programm und `flatpak run ...` erhalten die erwartete Argumentliste.
- Pfad mit Leerzeichen und Dateiname mit führendem Bindestrich.
- Ungültige Quotes, leeres Kommando und nicht existierbares Programm.
- Eigene Tile-Argumente werden nicht stillschweigend ignoriert.
- Erfolgs- und Fehlerstatus in der Oberfläche.

### Abnahmekriterien

- Alle Einstellungen bestehen den echten Persistenz- und Profil-Roundtrip.
- Externe AppImage-Prozesse erhalten keine gebündelten Bibliothekspfade.
- „Save & Apply“ reagiert auf jedes neue Bedienelement.

---

## Sprint 5: Ordner-Browse funktional vervollständigen

### Ziel

Der Browse-Modus fühlt sich wie ein konsistenter, bewusst read-only gehaltener Teil der Toolbox an
und verwendet dieselben Darstellungs- und Startregeln wie normale Tiles.

### Aufgaben

1. Eine gemeinsame Helper-Funktion `entries_for_current_view(ctx)` einführen, damit Auswahl,
   Aktivierung, Details und Kontextmenü im Browse-Modus dieselben sichtbaren Einträge verwenden.
2. Browse-spezifische Aktionen definieren:
   - Datei starten/öffnen.
   - Ordner betreten.
   - Pfad im Dateimanager öffnen.
   - Kopieren, Entfernen, Umbenennen und Tile-Eigenschaften im read-only Browse deaktivieren.
3. Kontextmenü und Detailansicht für Browse-Einträge aktivieren.
4. Alle Darstellungseinstellungen an `set_entries()` weitergeben, insbesondere:
   - `folder_show_file_count`
   - `show_tooltips`
   - Preview-/Overlay-Einstellungen
5. Stabile Browse-IDs aus normalisiertem Pfad ableiten, statt bei jeder Aktualisierung UUIDs neu zu
   erzeugen. So bleibt Auswahl bei einer Aktualisierung nachvollziehbar.
6. `PermissionError` und allgemeine `OSError` unterscheiden und dem Benutzer einen Statushinweis
   zeigen. Ein nicht lesbarer Ordner darf nicht wie ein leerer Ordner aussehen.
7. Fehler einzelner Verzeichniseinträge beim Sortieren isolieren; ein defekter Symlink darf nicht
   die komplette Ansicht abbrechen.
8. Versteckte Dateien weiterhin nach dokumentierter Regel behandeln.

### Tests

- Rechtsklick auf Datei und Ordner im Browse-Modus zeigt das passende Menü.
- Detailanzeige beschreibt den sichtbaren Browse-Eintrag.
- Tooltip- und Ordnerzähleroption werden an das Canvas weitergereicht.
- Auswahl bleibt nach einer Aktualisierung desselben Ordners erhalten.
- Permission denied, verschwundener Ordner, defekter Symlink und sehr langer Dateiname.
- Einzel-/Doppelklick respektieren die globale Startoption.
- Keine schreibende CRUD-Aktion verändert den durchsuchten Ordner.

### Abnahmekriterien

- Alle sichtbaren Browse-Einträge sind auswählbar, erklärbar und entsprechend ihrem Typ startbar.
- Fehlerzustände sind sichtbar und führen nicht zum Absturz.
- Browse-Modus besitzt keine abweichenden Tooltip-/Icon-/Prozessregeln.

---

## Sprint 6: FFmpeg-Download und AppImage-Lieferkette absichern

### Ziel

Das AppImage enthält ein überprüftes, reproduzierbares FFmpeg. Ein optionaler Runtime-Download
schreibt ausschließlich in Benutzerdaten und akzeptiert keinen ungeprüften Binärcode.

### Teil A: Reproduzierbarer Build

#### Aufgaben

1. Feste FFmpeg-Version und architekturspezifische Downloadmatrix definieren.
2. Für jedes Archiv URL, Version, Architektur und erwartete SHA-256-Prüfsumme versionieren.
3. Erst vollständig herunterladen, dann Hash prüfen, anschließend entpacken.
4. Bei Hashabweichung, unbekannter Architektur oder unvollständigem Download hart abbrechen.
5. `curl | tar` entfernen. Das Build-Skript darf nie ungeprüfte Netzwerkdaten direkt entpacken.
6. Offline-/CI-Modus unterstützen:
   - Explizite Pfade `TOOLBOX_FFMPEG_BINARY` und `TOOLBOX_FFPROBE_BINARY`.
   - Lokaler, zuvor verifizierter Cache.
   - Kein stiller Wechsel auf ein anderes Release.
7. Lizenz, Quelle, Version und Hash in `build-info.txt` und `THIRD_PARTY_NOTICES.md` aufnehmen.
8. `ffmpeg -version` und `ffprobe -version` innerhalb des AppDir-Smoke-Tests ausführen.

### Teil B: Sicherer Runtime-Download

#### Aufgaben

1. Downloadziel aus dem Projekt-/AppImage-Verzeichnis nach XDG-Benutzerdaten verschieben, zum
   Beispiel `~/.local/share/toolbox/ffmpeg/<version>/`.
2. Temporäre Datei im selben Ziel-Dateisystem verwenden und erst nach vollständiger Prüfung atomar
   umbenennen.
3. Hash, maximale Downloadgröße, Timeout und erwartete Dateinamen prüfen.
4. Archive nicht mit allgemeinem `extract()` entpacken:
   - Nur exakt erwartete reguläre Dateien übernehmen.
   - Symlinks, Hardlinks, absolute Pfade und `..`-Pfade ablehnen.
5. Abbruch beim Schließen unterstützen und temporäre Dateien zuverlässig entfernen.
6. Im AppImage den Downloadknopf ausblenden oder als „interne Version reparieren/aktualisieren“
   klar beschriften, wenn bereits ein verifiziertes FFmpeg gebündelt ist.
7. Architektur und Betriebssystem explizit prüfen; kein AMD64-Archiv auf ARM installieren.

### Tests

- Korrektes Archiv und korrekter Hash werden akzeptiert.
- Falscher Hash, abgeschnittener Download und HTTP-Fehler werden abgelehnt.
- Archiv mit `../`, absolutem Pfad, Symlink oder falschem Dateinamen wird abgelehnt.
- Abbruch hinterlässt keine halbe ausführbare Datei.
- Schreibgeschütztes AppImage-Verzeichnis wird nie als Installationsziel verwendet.
- x86_64, aarch64 und unbekannte Architektur.
- Offline-AppImage-Build mit lokal bereitgestellten Binärdateien.
- Zwei Builds mit identischem Input erzeugen identischen AppImage-Hash, soweit die vorhandene
  Buildkette Reproduzierbarkeit garantiert.

### Abnahmekriterien

- Kein ausführbarer Download wird ohne erfolgreiche Hashprüfung installiert oder gebündelt.
- Der AppImage-Build benötigt keine unversionierte „latest“-Quelle.
- Runtime-Download funktioniert in einem schreibgeschützten AppImage-Kontext.

---

## Sprint 7: Repository-, Desktopdatei- und Testhygiene

### Ziel

Der Standard-Testlauf, Git-Prüfungen und Desktopdatei-Validierung sind ohne Sonderbehandlung grün.

### Aufgaben

1. Experimentelle Root-Dateien entfernen oder in einen klar benannten, nicht von pytest
   gesammelten Entwicklerordner verschieben:
   - `test_clip.py`
   - `test_translucent.py`
   - `test_wrap.py`
   - `test_out.png`
   - `test_translucent.png`
2. Experimentcode darf keine Bilder in den Projektroot schreiben und gehört nicht in Release- oder
   Backupinhalte.
3. Die lokale Root-Desktopdatei bereinigen:
   - Keine ungültigen einfachen Quotes oder `&&` im `Exec=`-Feld.
   - Keine fest codierte persönliche Repositoryposition in einer verteilten Datei.
   - Bevorzugt nur `packaging/linux/toolbox.desktop` versionieren.
   - Einen lokalen Entwicklerstarter bei Bedarf durch ein separates Script generieren und
     ignorieren.
4. App-ID, `StartupWMClass`, Desktop-Dateiname und Fenstereigenschaften vereinheitlichen.
5. Alle Whitespace-Fehler beseitigen und Formatierungswerkzeuge als Dev-Abhängigkeit verfügbar
   machen.
6. Ruff-Regeln mindestens für unbenutzte Imports, undefinierte Namen und offensichtliche
   Fehlerklassen aktivieren.
7. Tests für neue Modellfelder `custom_title` und `custom_icon_path` sowie echte Sortierreihenfolge
   ergänzen. Sortiertests dürfen nicht nur temporär gesetzte Koordinaten prüfen.
8. Build-/Backup-Ausschlüsse für temporäre Dateien, Testbilder, `.bin`, `thirdparty` und lokale
   Downloadreste überprüfen. Bewusst benötigte Drittanbieterbinärdateien müssen getrennt von einem
   „Code-Backup“ behandelt oder klar dokumentiert werden.

### Tests

- `git diff --check`
- `desktop-file-validate packaging/linux/toolbox.desktop`
- Falls eine Root-Desktopdatei verbleibt: auch diese validieren.
- `appstreamcli validate --no-net packaging/linux/io.github.toolbox.Toolbox.appdata.xml`
- `bash -n scripts/*.sh packaging/linux/AppRun`
- `ruff check app main.py tests`
- `env -u LD_LIBRARY_PATH QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest -q`
- Test, dass keine Root-Experimente von pytest gesammelt werden.

### Abnahmekriterien

- Standard-pytest, Ruff, Compileall, Shellsyntax und Desktopvalidierung sind grün.
- `git status` enthält nach Tests keine neu erzeugten Artefakte.
- Keine persönliche absolute Pfadangabe wird als Projektstarter verteilt.

---

## Sprint 8: Linux-Mint-22.3- und AppImage-Releaseabnahme

### Ziel

Alle korrigierten Funktionen werden im echten Onefile-AppImage unter Linux Mint 22.3 geprüft.

### Automatisierte Releaseprüfungen

1. Vollständige Unit-/Integrations-/GUI-Suite in bereinigter Umgebung.
2. AppDir bauen und mit `scripts/test-appdir.sh` prüfen.
3. AppImage bauen und mit `scripts/check-appimage-content.sh` prüfen.
4. AppImage-Smoke-Tests:
   - Normale Ausführung.
   - `--appimage-extract-and-run`.
   - Umbenannter Dateiname.
   - Pfad mit Leerzeichen.
   - Symlink auf das AppImage.
   - Schreibgeschütztes Verzeichnis.
   - HiDPI.
5. Smoke-Test auch ausführen, während bereits eine normale Toolbox-Instanz läuft.
6. Inhalt prüfen:
   - Keine `.venv`, Tests, Testbilder, Logs oder Buildreste.
   - Erwartetes FFmpeg/FFprobe vorhanden, ausführbar und mit dokumentiertem Hash identisch.
   - Keine gebündelte glibc.

### Manuelle Linux-Mint-22.3-Testmatrix

1. **Start und Fenster:**
   - AppImage doppelklicken.
   - Zweiter Start aktiviert die bestehende Instanz.
   - Tray aus/an und Beenden über Tray prüfen.
2. **Drag-and-drop:**
   - Datei, Ordner, `.desktop`-Verknüpfung und URL-Verknüpfung hinzufügen.
   - Datei auf geeignete `.desktop`-Tile droppen.
   - Fehlerhafte Verknüpfung liefert verständliche Fehlermeldung.
3. **Icon-Sicherheit:**
   - Ausführbares Testscript hinzufügen.
   - Sicherstellen, dass es beim Hinzufügen, Suchen und Rendern nicht ausgeführt wird.
4. **Ordner und Suche:**
   - Viele Ordner hinzufügen, schnell suchen und Tabs wechseln.
   - UI bleibt bedienbar; keine Threadwarnung im Log.
   - Browse, Zurücknavigation, Kontextmenü und Details prüfen.
5. **Dateizuordnungen:**
   - Systemstandard sowie benutzerdefiniertes VLC/Flatpak testen.
   - Programme öffnen trotz AppImage-Bibliotheksumgebung zuverlässig.
6. **Einstellungen:**
   - Tooltips, Ordnerzähler, Tray und Dateizuordnungen speichern.
   - App vollständig beenden und neu starten.
   - Profil exportieren, Werte ändern und Profil wieder importieren.
7. **FFmpeg:**
   - Video-Vorschau mit gebündeltem FFmpeg auf einem System ohne System-FFmpeg testen.
   - Aktive Quelle und Pfad in den Einstellungen prüfen.
8. **Portabilität:**
   - AppImage auf Desktop und in einen anderen Ordner kopieren.
   - Ohne Repository und ohne virtuelle Python-Umgebung starten.

### Release-Abnahmekriterien

- Keine Sicherheits-, P0- oder P1-Befunde offen.
- Kein unbeabsichtigter Kindprozess bei Icon-Auflösung oder Canvas-Refresh.
- Keine `QThread`-Lebenszykluswarnung und keine merkliche UI-Blockade.
- Einstellungen überstehen Neustart und Profilroundtrip.
- AppImage-Smoke- und Linux-Mint-Manuelltests sind dokumentiert grün.
- SHA-256-Datei des finalen AppImages wird erst nach vollständig bestandener Abnahme veröffentlicht.

---

## 4. Empfohlene Testdateien

| Testdatei | Inhalt |
|---|---|
| `tests/test_icon_resolution_security.py` | Keine Ausführung, kein Hängen, Cacheverhalten |
| `tests/test_folder_count_service.py` | Poollimit, Cache, Abbruch, Widget-Lebenszyklus |
| `tests/test_size_calculator.py` | Deduplizierung, Timeout, Request-ID, Formatierung |
| `tests/test_main_window_lifecycle.py` | CloseEvent, Tray, Force-Quit, Shutdown |
| `tests/test_single_instance.py` | IPC, Race, stale Socket, Smoke-Isolation |
| `tests/test_settings_persistence.py` | QSettings-, Dirty-State- und Migrationsroundtrip |
| `tests/test_file_associations.py` | Bereinigte Umgebung, Argumente, Fehlerstatus |
| `tests/test_folder_browse.py` | Sichtbare Entries, Kontextmenü, OSError, Settings |
| `tests/test_ffmpeg_downloader.py` | Hash, Archivschutz, Architektur, atomare Installation |
| `tests/test_appimage_packaging.py` | Gepinnte FFmpeg-Metadaten und Inhaltsprüfung |

## 5. Definition of Done für jeden Sprint

Ein Sprint ist erst abgeschlossen, wenn alle folgenden Punkte erfüllt sind:

1. Implementierung und Fehlerpfade sind vorhanden.
2. Neue Regressionstests sind grün und würden ohne den Fix fehlschlagen.
3. Der vollständige Standard-Testlauf ist grün.
4. Keine neuen Ausgaben von `git diff --check`.
5. Keine temporären Dateien oder Testartefakte im Arbeitsverzeichnis.
6. Relevante Dokumentation und Hilfetexte entsprechen dem tatsächlichen Verhalten.
7. Bei Prozess-, Thread- oder AppImage-Änderungen wurde mindestens ein echter Integrations- oder
   Smoke-Test ausgeführt; reine Mocks reichen nicht.
8. Der Sprint wird in einem eigenen, nachvollziehbaren Commit abgeschlossen.

## 6. Empfohlene Commit-Reihenfolge

1. `test: capture Gemini regression baseline`
2. `security: stop executing targets during icon resolution`
3. `fix: centralize and bound filesystem background jobs`
4. `fix: unify tray shutdown and single-instance lifecycle`
5. `fix: complete settings and file-association integration`
6. `fix: complete read-only folder browsing behavior`
7. `security: pin and verify bundled FFmpeg artifacts`
8. `chore: restore repository and desktop-entry hygiene`
9. `test: verify Linux Mint 22.3 AppImage release acceptance`

Die Commits sollten nicht zusammengefasst werden, solange die Abnahme läuft. Dadurch kann ein
fehlerhafter Sprint gezielt zurückgenommen werden, ohne bereits verifizierte Sicherheitsfixes zu
verlieren.
