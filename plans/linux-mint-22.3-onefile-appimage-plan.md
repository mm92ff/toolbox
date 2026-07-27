# Implementierungsplan: Onefile-AppImage für Linux Mint 22.3

## 1. Dokumentstatus

- Status: Technisch umgesetzt und nachauditiert am 27.07.2026; automatisierte
  Abnahme bestanden, externe manuelle Releasechecks separat ausgewiesen
- Zielsystem: Linux Mint 22.3 „Zena“, x86_64
- Paketbasis: Ubuntu Noble
- Zielartefakt: genau eine auszuliefernde Datei `Toolbox-<version>-x86_64.AppImage`
- Referenzsystem für Build und Abnahme: Linux Mint 22.3, glibc 2.39
- Anwendung: Toolbox, Python/PySide6
- Planablage: `plans/linux-mint-22.3-onefile-appimage-plan.md`

## 2. Bedeutung von „Onefile AppImage“

Das Release besteht aus genau einer ausführbaren `.AppImage`-Datei. Es wird kein
zusätzlicher Installationsordner, kein Python und kein separat installiertes PySide6
benötigt.

Intern wird ein PyInstaller-`onedir`-Payload in ein AppDir gelegt. `appimagetool`
komprimiert dieses AppDir anschließend zu genau einer AppImage-Datei.

Diese Aufteilung ist bewusst gewählt:

1. Ein AppImage ist bereits ein Onefile-Container.
2. Ein zusätzliches PyInstaller-`onefile` würde beim Start nochmals nach `/tmp`
   entpacken.
3. Ein PyInstaller-`onedir`-Payload kann direkt aus dem schreibgeschützt gemounteten
   AppImage gestartet werden.
4. Externe Prozesse und Qt-Plugins lassen sich in dieser Form zuverlässiger testen.
5. Für den Benutzer bleibt das Ergebnis unverändert eine einzige Datei.

Nicht vorgesehen ist damit ein verschachteltes
„PyInstaller-onefile innerhalb eines AppImage“. Falls dies später ausdrücklich
gefordert wird, wird es als alternative, langsamere Buildvariante separat bewertet.

## 3. Zielbild

Der geplante Buildablauf lautet:

```text
Quellcode
   |
   v
isolierte Python-Buildumgebung
   |
   v
PyInstaller onedir
   |
   v
Toolbox.AppDir
├── AppRun
├── toolbox.desktop
├── toolbox.png
└── usr/lib/toolbox/
    ├── toolbox
    └── _internal/...
   |
   v
appimagetool
   |
   v
Toolbox-<version>-x86_64.AppImage
```

Das AppImage:

- startet per Doppelklick und aus dem Terminal;
- läuft ohne systemweit installiertes Python oder PySide6;
- speichert Konfiguration ausschließlich im Benutzerprofil;
- startet Linux-Programme ohne vererbte, inkompatible Bundle-Bibliotheken;
- unterstützt Dateien, Ordner, ausführbare Programme und Skripte;
- verwendet optional ein systemweit vorhandenes FFmpeg;
- zeigt unter Cinnamon/X11 das korrekte Symbol und den korrekten Fensternamen;
- liefert verständliche Fehler, wenn ein Ziel nicht gestartet werden kann.

## 4. Umfang

### 4.1 Im Umfang

- Linux-Mint-22.3-Unterstützung für x86_64
- stabiles Linux-Verhalten der bestehenden Launcher-Funktionen
- PyInstaller-`onedir`-Build für den internen Payload
- AppDir und finale Onefile-AppImage
- Desktop-Datei und Anwendungssymbol
- reproduzierbares Linux-Buildskript
- isolierte Build-Abhängigkeiten
- automatisierte Unit-, Integrations- und Pakettests
- manuelle Abnahme unter Linux Mint 22.3
- Dokumentation für Build, Ausführung und Fehlerdiagnose
- Lizenz- und Drittanbieterhinweise für das tatsächlich ausgelieferte Bundle

### 4.2 Nicht im Umfang

- ARM64-AppImage
- Linux Mint 21.x oder andere ältere glibc-Ziele
- DEB-, Flatpak- oder Snap-Paket
- automatische Installation in das Startmenü
- Auto-Updater
- Codesignierung oder GPG-Signierung im ersten AppImage-Sprint
- zwingend gebündeltes FFmpeg
- vollständige Windows-/Linux-Synchronisierung vorhandener Pfade
- Implementierung einer allgemeinen Linux-Rechteerhöhung ohne gesondertes
  Sicherheitskonzept

## 5. Geplante Dateien

Die genaue Benennung darf während der Implementierung angepasst werden. Erwartet
werden mindestens:

```text
packaging/
├── linux/
│   ├── AppRun
│   ├── toolbox.desktop
│   └── toolbox.appdata.xml          # optional, aber empfohlen
└── README.md

scripts/
├── build-appimage.sh
├── test-appdir.sh
└── test-appimage.sh

tests/
├── test_linux_launch.py
├── test_process_environment.py
├── test_app_identity.py
└── test_appimage_smoke.py

toolbox_linux.spec
requirements-build-linux.txt
```

Voraussichtliche Änderungen an bestehenden Dateien:

```text
main.py
app/constants.py
app/services/system_utils.py
app/services/video_thumbnails.py
app/features/entries/launching.py
app/ui/tabs/settings_tab_sections.py
README.md
THIRD_PARTY_NOTICES.md
.gitignore
```

## 6. Qualitäts- und Abnahmeregeln

Jeder Sprint endet nur dann, wenn:

1. seine automatisierten Tests grün sind;
2. `git diff --check` keine Fehler meldet;
3. keine generierten Buildartefakte versehentlich versioniert wurden;
4. vorhandene Windows-Tests weiterhin bestehen;
5. neu eingeführte Linux-Verzweigungen getestet sind;
6. die Sprint-Abnahmekriterien erfüllt und dokumentiert sind.

Ein Fehler in Programmstart, Persistenz, externem Prozessstart oder Qt-Plugin-Laden
ist releaseblockierend.

---

# Sprint 0: Baseline, Entscheidungen und reproduzierbare Umgebung

## Ziel

Eine messbare Ausgangsbasis schaffen und Buildentscheidungen festschreiben, bevor
Anwendungscode verändert wird.

## Aufgaben

1. Aktuellen Stand auf Linux Mint 22.3 in einer isolierten virtuellen Umgebung
   installieren.
2. Python-, PySide6-, PyInstaller- und AppImage-Werkzeugversionen erfassen.
3. Einen vollständigen Baseline-Testlauf ausführen.
4. Den Start aus dem Quellcode mit `QT_DEBUG_PLUGINS=1` prüfen.
5. Architekturentscheidung dokumentieren:
   - finales Onefile-AppImage;
   - interner PyInstaller-`onedir`-Payload;
   - x86_64;
   - Linux Mint 22.3 als ältestes zugesichertes Ziel.
6. Festlegen, ob FFmpeg im ersten Release:
   - nur als Systemabhängigkeit unterstützt wird; oder
   - explizit gebündelt wird.
7. Buildabhängigkeiten in `requirements-build-linux.txt` fest versionieren.
8. Prüfen, ob der vorhandene lokale `appimagetool`-Build ersetzt oder durch
   Download, Version und SHA-256-Prüfsumme reproduzierbar eingebunden wird.

## Tests

### S0-T01: Baseline-Unit-Tests

```bash
python -m pytest -q
```

Erwartung: Alle vorhandenen Tests bestehen oder bekannte, bereits vorhandene Fehler
werden vor Beginn der Implementierung dokumentiert.

### S0-T02: Quellcode-Start

```bash
QT_DEBUG_PLUGINS=1 python main.py
```

Erwartung:

- Hauptfenster erscheint;
- `qxcb` wird geladen;
- Symbol wird angezeigt;
- keine fehlenden Qt-Bibliotheken;
- Anwendung beendet sich sauber.

### S0-T03: Plattformdaten

Zu protokollieren:

```bash
uname -m
python --version
ldd --version
python -c "import PySide6; print(PySide6.__version__)"
python -m PyInstaller --version
appimagetool --version
```

## Abnahmekriterien

- Baseline ist dokumentiert.
- Buildversionen sind festgelegt.
- FFmpeg-Strategie ist entschieden.
- Keine Produktivdatei wurde in diesem Sprint funktional verändert.

---

# Sprint 1: Linux-fähige Prozess- und Launcher-Schicht

## Ziel

Die Kernfunktion der Toolbox – das Starten externer Programme – unter Linux korrekt
und sicher machen.

## Aufgaben

1. Eine Hilfsfunktion für bereinigte externe Prozessumgebungen implementieren.
2. Unter Linux:
   - `LD_LIBRARY_PATH` aus `LD_LIBRARY_PATH_ORIG` wiederherstellen;
   - `LD_LIBRARY_PATH` entfernen, wenn kein Originalwert existiert;
   - die Umgebung der Toolbox selbst unverändert lassen.
3. Alle Systemprozesse über diese Umgebung starten:
   - Tool-Einträge;
   - `xdg-open` oder `gio open`;
   - System-FFmpeg;
   - weitere externe Hilfsprogramme.
4. Linux-Argumente sicher mit `shlex.split` oder einer eindeutig dokumentierten
   Argumentsemantik verarbeiten.
5. Konfiguriertes Arbeitsverzeichnis validieren und an `Popen` übergeben.
6. `wait=True` unter Linux unterstützen, ohne die GUI unkontrolliert einzufrieren.
   Falls synchrones Warten die Oberfläche blockieren würde, wird ein Worker oder
   ein nicht blockierender Qt-Prozess verwendet.
7. Nicht ausführbare Dateien über die Desktop-Standardanwendung öffnen.
8. Ordner weiterhin über `xdg-open`/`gio open` öffnen.
9. Ausführbare Dateien und Skripte direkt starten.
10. Nicht ausführbare Skripte mit verständlicher Meldung ablehnen oder über ihre
    Dateizuordnung öffnen.
11. Linux-Verhalten für Fensterstatus festlegen:
    - bevorzugt Linux-unwirksame Werte ausblenden;
    - alternativ nur `normal` unterstützen und andere Werte klar ignorieren.
12. „Run as Administrator“ unter Linux ausblenden oder deaktivieren.
13. Keine automatische `sudo`- oder Shell-Ausführung einführen.

## Tests

### S1-T01: Bereinigung von `LD_LIBRARY_PATH`

Testfälle:

- `LD_LIBRARY_PATH_ORIG` vorhanden;
- `LD_LIBRARY_PATH_ORIG` leer;
- kein Originalwert vorhanden;
- andere Umgebungsvariablen bleiben erhalten;
- Elternprozessumgebung bleibt unverändert.

### S1-T02: Direkt ausführbare Datei

Eine temporäre ausführbare Datei wird gestartet. Erwartung:

- Start erfolgreich;
- korrektes Arbeitsverzeichnis;
- übergebene Argumente kommen unverändert beziehungsweise gemäß definierter
  Parsingregel an;
- bereinigte Bibliotheksumgebung wird vererbt.

### S1-T03: Dateiname mit Leerzeichen

Pfad und Arbeitsverzeichnis enthalten Leerzeichen. Erwartung: kein Shell-Parsing,
kein Abschneiden, kein unerwartetes Quoting.

### S1-T04: Nicht ausführbares Dokument

Eine normale Textdatei wird nicht direkt mit `Popen([datei])` gestartet, sondern
über den Desktop-Öffner übergeben.

### S1-T05: Ordner öffnen

Ein existierender Ordner wird mit bereinigter Umgebung geöffnet. Fehlendes
`xdg-open`/`gio` führt zu einer verständlichen Fehlermeldung.

### S1-T06: Fehlende und ungültige Ziele

Testfälle:

- nicht vorhandener Pfad;
- Nullbyte;
- ungültiges Arbeitsverzeichnis;
- vorhandene, aber nicht zugängliche Datei;
- fehlende Ausführungsrechte.

### S1-T07: Kein Shell-Injection-Pfad

Argumente wie `$(...)`, Backticks, Semikolon und Leerzeichen werden nie durch
`shell=True` interpretiert.

### S1-T08: UI-Plattformoptionen

Unter Linux:

- Administratoroption ist nicht aktiv auswählbar;
- Windows-spezifischer Fensterstatus ist ausgeblendet oder klar deaktiviert;
- bestehende gespeicherte Windows-Werte führen nicht zum Absturz.

### S1-T09: Windows-Regression

Alle vorhandenen Windows-Launcher-Tests bleiben grün. Windows-Codepfade werden nicht
durch die Linux-Umgebungsbereinigung verändert.

## Abnahmekriterien

- Externe Linux-Programme starten mit Systembibliotheken.
- Argumente und Arbeitsverzeichnis funktionieren.
- Dokumente und Ordner verwenden den Desktop-Öffner.
- Es gibt keine Shell-Injection.
- Windows-Verhalten bleibt unverändert.

---

# Sprint 2: Stabile App-Identität, Persistenz und Linux-UI

## Ziel

Fenstertitel, Desktop-ID und Konfigurationspfade bleiben unabhängig vom Dateinamen
des AppImage stabil.

## Aufgaben

1. Eine feste Produktidentität definieren:
   - Produktname `Toolbox`;
   - ausführbarer Name `toolbox`;
   - Desktop-ID, beispielsweise `io.github.toolbox.Toolbox`;
   - stabiler Konfigurationsordner `toolbox`.
2. `sys.argv[0]` nicht mehr als alleinige persistente Produktidentität verwenden.
3. `$XDG_CONFIG_HOME` berücksichtigen; ohne Variable auf `~/.config` zurückfallen.
4. QSettings-Organisation und Anwendungsname stabil setzen.
5. Vorhandene Konfigurationsdaten aus bisherigen Namen nicht automatisch löschen.
6. Eine dokumentierte, einmalige Migrationsstrategie definieren.
7. Linux-spezifische UI-Texte korrigieren:
   - FFmpeg-Platzhalter ohne `C:\...`;
   - „Run as Administrator“ plattformgerecht behandeln;
   - generische Beispiele für Linux-Argumente.
8. Unter Linux den Desktop-Dateinamen an Qt melden, falls für korrekte
   Fenstergruppierung erforderlich.

## Tests

### S2-T01: Stabiler Name

Die Anwendung wird unter mehreren Dateinamen gestartet. Erwartung: Fenstertitel,
Desktop-ID und Konfigurationsverzeichnis bleiben gleich.

### S2-T02: XDG-Konfiguration

Mit temporärem `XDG_CONFIG_HOME` wird ausschließlich dort geschrieben.

### S2-T03: Schreibgeschütztes AppImage

Keine Funktion versucht, in `$APPDIR`, neben das AppImage oder in `_MEIPASS` zu
schreiben.

### S2-T04: Persistenz-Neustart

Tabs, Positionen, Darstellung und FFmpeg-Einstellungen werden gespeichert, die
Anwendung wird neu gestartet und alle Werte werden korrekt geladen.

### S2-T05: Migration

Vorhandene Konfiguration eines vorherigen Namens wird entsprechend der gewählten
Strategie:

- gefunden und übernommen; oder
- bewusst nicht übernommen und klar dokumentiert.

### S2-T06: UI-Plattformtexte

Unter Linux erscheinen keine irreführenden zwingenden Windows-Pfade oder
Windows-Funktionen.

## Abnahmekriterien

- Release-Dateiname beeinflusst keine Benutzerdaten.
- XDG-Pfade funktionieren.
- Alle Schreibzugriffe liegen im Benutzerprofil.
- Linux-UI ist konsistent.

---

# Sprint 3: PyInstaller-Linux-Payload

## Ziel

Eine eigenständig lauffähige PyInstaller-`onedir`-Ausgabe erzeugen, bevor sie in ein
AppImage verpackt wird.

## Aufgaben

1. Separate `toolbox_linux.spec` erstellen.
2. `COLLECT` für einen `onedir`-Build verwenden.
3. Payloadname auf `toolbox` festlegen.
4. `upx=False` setzen, da das AppImage später selbst komprimiert.
5. Nur benötigte PySide6-Module aufnehmen.
6. Erforderliche Qt-Plugins verifizieren:
   - `platforms/libqxcb.so`;
   - relevante Bildformatplugins;
   - optional Wayland-Plugins.
7. `one.png` als Laufzeitressource aufnehmen.
8. Symlinks im PyInstaller-Bundle erhalten.
9. Automatische FFmpeg-Übernahme aus dem Build-`PATH` entfernen.
10. FFmpeg nur bei expliziter Buildoption bündeln.
11. PyInstaller-Warnungen prüfen und klassifizieren.
12. Mit `ldd` nach nicht aufgelösten Abhängigkeiten suchen.
13. Sicherstellen, dass glibc nicht unzulässig mitgebündelt wird.
14. Buildartefakte in `.gitignore` aufnehmen.

## Tests

### S3-T01: Sauberer Build

```bash
python -m PyInstaller --clean --noconfirm toolbox_linux.spec
```

Erwartung: Build endet mit Status 0.

### S3-T02: AppDir-Vorstufe ohne System-Python

Der erzeugte Payload wird mit einer Umgebung gestartet, in der Projekt-venv und
Python-Site-Packages nicht im `PATH` beziehungsweise `PYTHONPATH` liegen.

### S3-T03: Qt-Plugin-Smoke-Test

```bash
QT_DEBUG_PLUGINS=1 dist/toolbox/toolbox
```

Erwartung: `qxcb` wird aus dem Payload geladen; keine Vermischung mit einer
systemweiten PySide6-Installation.

### S3-T04: Abhängigkeitsprüfung

Alle ELF-Dateien werden auf `not found` geprüft. Erwartung: keine unbeabsichtigt
fehlenden Bibliotheken.

### S3-T05: Ressourcen

Fenster- und Anwendungssymbol werden aus dem Bundle geladen.

### S3-T06: Externe Programme aus Frozen App

Aus der PyInstaller-Ausgabe werden mindestens gestartet:

- `/usr/bin/true`;
- ein temporäres Testskript;
- `xdg-open` in kontrollierter/mocking-basierter Form;
- optional System-FFmpeg.

Dabei darf kein Bundle-`LD_LIBRARY_PATH` an Systemprogramme weitergegeben werden.

### S3-T07: FFmpeg-Reproduzierbarkeit

- Ohne explizite Option wird kein FFmpeg gebündelt.
- Mit expliziter Option wird genau die angegebene Binary verwendet.
- Buildinhalt ändert sich nicht nur deshalb, weil auf dem Builder zufällig FFmpeg
  installiert ist.

## Abnahmekriterien

- `dist/toolbox/` läuft selbstständig.
- Qt und Ressourcen werden korrekt geladen.
- Externe Systemprogramme funktionieren.
- Keine unerwartete FFmpeg-Binary befindet sich im Payload.

---

# Sprint 4: AppDir und finale Onefile-AppImage

## Ziel

Den getesteten PyInstaller-Payload zu einer einzigen AppImage-Datei verpacken.

## Aufgaben

1. Reproduzierbare AppDir-Struktur erzeugen.
2. Minimalen `AppRun` verwenden:
   - Pfade relativ zu `$APPDIR`;
   - keine unnötige globale Änderung von `LD_LIBRARY_PATH`;
   - Prozess mit `exec` ersetzen;
   - Aufrufargumente vollständig weiterreichen.
3. `toolbox.desktop` erstellen:
   - `Type=Application`;
   - `Name=Toolbox`;
   - `Exec=toolbox`;
   - `Icon=toolbox`;
   - `Terminal=false`;
   - registrierte Kategorie `Utility`;
   - stabile Desktop-ID.
4. PNG-Symbol in korrekter hicolor-Struktur ablegen.
5. Root-Symlinks oder von AppImage erwartete Root-Metadaten korrekt erzeugen.
6. Optional AppStream-Metadaten hinzufügen.
7. `desktop-file-validate` ausführen.
8. `appimagetool` mit expliziter Architektur ausführen.
9. Ergebnisname ohne Leerzeichen und ohne unnötiges Wort `Linux` bilden.
10. SHA-256-Prüfsumme erzeugen.
11. Dateigröße erfassen.
12. Buildprotokoll mit Werkzeugversionen ausgeben.

## Tests

### S4-T01: AppDir direkt starten

```bash
./Toolbox.AppDir/AppRun
```

Erwartung: vollständiger Start noch vor der AppImage-Komprimierung.

### S4-T02: Desktop-Datei

```bash
desktop-file-validate Toolbox.AppDir/toolbox.desktop
```

Erwartung: keine Fehler.

### S4-T03: Onefile-Ergebnis

Nach dem Build wird genau eine auszuliefernde Anwendung erzeugt:

```text
Toolbox-<version>-x86_64.AppImage
```

Neben dieser Datei werden für Benutzer keine Payload-Ordner benötigt.

### S4-T04: Ausführungsrechte

Nach `chmod +x` startet das AppImage per Terminal und Dateimanager.

### S4-T05: FUSE-Start

Normaler AppImage-Start auf Linux Mint 22.3 mit vorhandenem `libfuse2t64`.

### S4-T06: Extract-and-run

```bash
./Toolbox-<version>-x86_64.AppImage --appimage-extract-and-run
```

Erwartung: Start funktioniert auch über den dokumentierten FUSE-Fallback.

### S4-T07: Argumentweitergabe

Testargumente werden durch AppImage-Runtime und `AppRun` unverändert an den Payload
weitergegeben.

### S4-T08: AppImage-Inhalt

Mit `--appimage-extract` prüfen:

- Desktop-Datei vorhanden;
- Symbol vorhanden;
- `AppRun` ausführbar;
- Payload vollständig;
- keine `.venv`;
- kein Testcache;
- keine Buildlogs;
- keine Windows-BAT-Dateien;
- kein zufällig gebündeltes FFmpeg.

### S4-T09: Relokation

Das AppImage wird aus folgenden Pfaden gestartet:

- Benutzer-Downloadordner;
- Pfad mit Leerzeichen;
- schreibgeschützter Ordner;
- symbolischer Link.

Benutzerdaten bleiben im stabilen Konfigurationsverzeichnis.

## Abnahmekriterien

- Genau eine AppImage-Datei ist für die Auslieferung nötig.
- AppDir- und AppImage-Start funktionieren.
- Desktop-Metadaten sind gültig.
- FUSE- und Extract-and-run-Pfade sind geprüft.

---

# Sprint 5: Funktions-, Desktop- und Kompatibilitätstests

## Ziel

Das fertige AppImage als reale Desktopanwendung auf einem sauberen Zielsystem
abnehmen.

## Testmatrix

| Bereich | Mindesttest |
|---|---|
| System | Linux Mint 22.3 Cinnamon x86_64 |
| Display | X11 |
| Optional | Wayland-Sitzung |
| Skalierung | 100 % und HiDPI |
| Python | auf Zielsystem nicht erforderlich |
| PySide6 | auf Zielsystem nicht erforderlich |
| FFmpeg | einmal nicht installiert, einmal systemweit installiert |
| FUSE | normaler Start und Extract-and-run |
| Pfad | normal, Leerzeichen, Symlink, schreibgeschützter Ordner |

## Automatisierte End-to-End-Tests

### S5-T01: Erststart

- kein bestehender Konfigurationsordner;
- Fenster erscheint;
- Standardtab vorhanden;
- keine Datei wird neben das AppImage geschrieben.

### S5-T02: Persistenz

- Tab hinzufügen;
- Tool hinzufügen;
- Position ändern;
- Einstellungen ändern;
- beenden;
- neu starten;
- Zustand vollständig wiederhergestellt.

### S5-T03: Programmstart

- ELF-Programm;
- ausführbares Shellskript;
- Pfad mit Leerzeichen;
- Argumente mit Leerzeichen;
- benutzerdefiniertes Arbeitsverzeichnis;
- nicht vorhandenes Ziel.

### S5-T04: Datei- und Ordneröffnung

- Textdatei mit Standardanwendung;
- Bilddatei mit Standardanwendung;
- Verzeichnis mit Dateimanager;
- Konfigurationsordner aus der Toolbox.

### S5-T05: Medienvorschau ohne FFmpeg

- Bildvorschau funktioniert;
- Videovorschau meldet FFmpeg als nicht gefunden;
- Anwendung bleibt stabil.

### S5-T06: Medienvorschau mit System-FFmpeg

- FFmpeg wird aus System-`PATH` erkannt;
- Vorschaubild wird erzeugt;
- FFmpeg lädt Systembibliotheken, nicht Bundle-Bibliotheken;
- Cache wird im Benutzerprofil geschrieben.

### S5-T07: Drag-and-drop

- ausführbare Datei;
- Skript;
- Dokument;
- Ordner;
- ungültiger Pfad.

### S5-T08: Symbolintegration

- Fenstersymbol;
- Taskleisten-/Panel-Symbol;
- Dateimanageranzeige;
- Desktop-Integration, sofern ein AppImage-Integrator verwendet wird.

### S5-T09: Sauberes Beenden

- normaler Fensterabschluss;
- gespeicherter Zustand konsistent;
- keine zurückbleibenden `_MEI*`-Verzeichnisse aus verschachteltem
  PyInstaller-Onefile;
- keine Zombieprozesse.

### S5-T10: Fehlerdiagnose

Fehler beim Start eines Tools erzeugen:

- verständlichen Dialog;
- keinen Anwendungsabsturz;
- eine nützliche Logmeldung ohne sensible vollständige Benutzerpfade, soweit nicht
  für die Diagnose nötig.

## Manuelle Abnahmecheckliste

- [ ] Doppelklick startet die Anwendung.
- [ ] Start aus Terminal funktioniert.
- [ ] Symbol und Fenstertitel sind korrekt.
- [ ] Anwendung lässt sich frei verschieben und skalieren.
- [ ] Tabs und Einstellungen bleiben nach Neustart erhalten.
- [ ] Programme starten mit Argumenten.
- [ ] Dateien öffnen mit Standardanwendungen.
- [ ] Ordner öffnen im Dateimanager.
- [ ] FFmpeg-Status ist unter Linux verständlich.
- [ ] Kein Administrator-Schalter verspricht eine nicht vorhandene Funktion.
- [ ] Beenden hinterlässt keinen fehlerhaften Zustand.
- [ ] AppImage funktioniert nach Verschieben und Umbenennen.

## Abnahmekriterien

- Alle releaseblockierenden Tests sind grün.
- Keine Abhängigkeit von installiertem Python/PySide6.
- Kernfunktionen sind unter Cinnamon/X11 bestätigt.
- Bekannte Einschränkungen sind dokumentiert.

---

# Sprint 6: Dokumentation, Releasehärtung und reproduzierbarer Build

## Ziel

Den Build wiederholbar und das Artefakt veröffentlichungsfähig machen.

## Aufgaben

1. README um Linux-Mint-Anweisungen ergänzen:
   - AppImage ausführbar machen;
   - starten;
   - FUSE-Hinweis;
   - Extract-and-run-Fallback;
   - Konfigurationspfad;
   - optionales FFmpeg.
2. Buildanleitung dokumentieren.
3. Exakte Buildwerkzeugversionen dokumentieren.
4. Drittanbieterhinweise ergänzen:
   - Python-Laufzeit;
   - PySide6/Qt;
   - Shiboken;
   - PyInstaller-Bootloader;
   - AppImage-Runtime;
   - optional FFmpeg.
5. Lizenzdateien in das AppImage aufnehmen, soweit erforderlich.
6. Generierte Dateien eindeutig von versionierten Quellen trennen.
7. Build zweimal aus sauberem Zustand durchführen.
8. Abweichungen der SHA-256-Prüfsummen untersuchen.
9. Mindestens funktionale Reproduzierbarkeit garantieren; bit-identische Builds
   werden nur zugesichert, wenn Zeitstempel und Toolausgaben kontrolliert sind.
10. Release-Checkliste und bekannte Einschränkungen erstellen.

## Tests

### S6-T01: Clean-room-Build

Aus einem frischen Checkout und einer neuen virtuellen Umgebung entsteht das
AppImage ohne Zugriff auf vorherige Buildordner.

### S6-T02: Keine unversionierten Voraussetzungen

Das Buildskript prüft alle benötigten Programme und bricht mit konkreter Meldung ab,
wenn eines fehlt.

### S6-T03: Wiederholungsbuild

Zwei Builds mit denselben Eingaben werden auf:

- Dateiname;
- enthaltene Dateiliste;
- Abhängigkeiten;
- Werkzeugversionen;
- Prüfsummenabweichungen

verglichen.

### S6-T04: Lizenzinhalt

Alle tatsächlich mitgelieferten Komponenten sind in den Drittanbieterhinweisen
aufgeführt. Nicht gebündeltes System-FFmpeg wird nicht fälschlich als enthalten
deklariert.

### S6-T05: Releaseartefakte

Erwartete Ausgabe:

```text
Toolbox-<version>-x86_64.AppImage
Toolbox-<version>-x86_64.AppImage.sha256
```

Die SHA-256-Datei ist Begleitmetadata; die Anwendung selbst bleibt eine einzelne
AppImage-Datei.

## Abnahmekriterien

- Clean-room-Build erfolgreich.
- Dokumentation vollständig.
- Lizenzprüfung abgeschlossen.
- Releasecheckliste vollständig grün.

---

# 7. Priorisierte Gesamttestliste

## P0 – releaseblockierend

1. AppImage startet auf sauberem Linux Mint 22.3.
2. Qt-`qxcb`-Plugin wird geladen.
3. Externe Programme erhalten kein Bundle-`LD_LIBRARY_PATH`.
4. Ausführbare Programme starten mit Argumenten und Arbeitsverzeichnis.
5. Konfiguration wird außerhalb des AppImage geschrieben und nach Neustart geladen.
6. AppImage funktioniert nach Verschieben und Umbenennen.
7. AppImage funktioniert mit FUSE oder dokumentiertem Extract-and-run-Fallback.
8. Kein systemweites Python oder PySide6 erforderlich.
9. Keine nicht aufgelösten ELF-Abhängigkeiten.
10. Keine Regression der bestehenden Kern- und Windows-Tests.

## P1 – vor öffentlichem Release erforderlich

1. Dokumente und Ordner öffnen über Standardanwendungen.
2. Bildvorschauen funktionieren.
3. System-FFmpeg funktioniert mit bereinigter Umgebung.
4. Desktop-Datei ist valide.
5. Symbol und Fenstergruppierung sind korrekt.
6. HiDPI-Darstellung ist brauchbar.
7. Fehlerdialoge sind verständlich.
8. Clean-room-Build ist erfolgreich.
9. Drittanbieterlizenzen sind vollständig.

## P2 – empfohlen

1. Wayland-Smoke-Test.
2. AppStream-Metadaten.
3. reproduzierbare Prüfsummen.
4. automatisierter CI-Build.
5. automatisierter Test auf MATE oder Xfce.
6. GPG-Signierung und Updateinformationen.

---

# 8. Risiken und Gegenmaßnahmen

| Risiko | Auswirkung | Gegenmaßnahme |
|---|---|---|
| PyInstaller-Bibliotheken gelangen in externe Prozesse | gestartete Systemprogramme funktionieren nicht | bereinigte Prozessumgebung und Frozen-Integrationstests |
| Qt-XCB-Abhängigkeit fehlt | Anwendung startet nicht | `QT_DEBUG_PLUGINS`, `ldd`, Test auf sauberem Mint |
| verschachteltes Onefile | langsamer Start und temporäre Extraktion | PyInstaller onedir im finalen Onefile-AppImage |
| Build übernimmt zufälliges System-FFmpeg | nicht reproduzierbar, Lizenzrisiko | nur explizite FFmpeg-Buildoption |
| dynamischer App-Name | neue Konfiguration je Release | feste Produkt- und Desktop-ID |
| Windows-Optionen bleiben sichtbar | irreführende oder fehlerhafte Linux-UI | plattformabhängige UI-Fähigkeiten |
| FUSE 2 fehlt | normaler AppImage-Start scheitert | `libfuse2t64` dokumentieren und Extract-and-run testen |
| Build auf zu neuem glibc | läuft nicht auf älteren Systemen | Mint 22.3 als ältestes zugesichertes Ziel festlegen |
| Symlinks gehen beim Kopieren verloren | größeres oder defektes PyInstaller-Bundle | `cp -a`/`rsync -a` und Symlink-Test |
| AppImage-AppRun verändert globale Pfade | Konflikte mit Systemprogrammen | minimales AppRun ohne unnötiges `LD_LIBRARY_PATH` |

---

# 9. Definition of Done

Die Linux-Mint-22.3-AppImage-Unterstützung ist abgeschlossen, wenn:

1. `Toolbox-<version>-x86_64.AppImage` als einzelne Datei gebaut wird.
2. Das Artefakt auf einer sauberen Linux-Mint-22.3-Installation startet.
3. Python und PySide6 auf dem Zielsystem nicht installiert sein müssen.
4. Programme, Skripte, Dateien und Ordner korrekt behandelt werden.
5. externe Systemprogramme keine Bundle-Bibliotheken erben.
6. Argumente und Arbeitsverzeichnisse unter Linux funktionieren.
7. Konfiguration und Cache stabil im Benutzerprofil liegen.
8. Fenstertitel, Desktop-ID und Konfigurationsname versionsunabhängig sind.
9. Qt-Plugins, Symbole und Desktop-Metadaten validiert sind.
10. FUSE- und Extract-and-run-Start getestet sind.
11. alle P0- und P1-Tests grün sind.
12. vorhandene Tests keine Regression zeigen.
13. Build und Release vollständig dokumentiert sind.
14. Drittanbieter- und Lizenzhinweise den tatsächlichen Bundleinhalt abbilden.

## 10. Empfohlene Ausführungsreihenfolge

```text
Sprint 0
  Baseline und Versionen
      |
      v
Sprint 1
  Linux-Prozessstart und Umgebungsisolation
      |
      v
Sprint 2
  stabile Identität und Persistenz
      |
      v
Sprint 3
  PyInstaller-onedir-Payload
      |
      v
Sprint 4
  AppDir und Onefile-AppImage
      |
      v
Sprint 5
  Zielsystem- und Funktionsabnahme
      |
      v
Sprint 6
  Dokumentation und Releasehärtung
```

Sprint 1 ist der wichtigste technische Sprint, weil die Toolbox externe Programme
startet. Sprint 3 darf erst als abgeschlossen gelten, wenn diese Programme auch aus
dem Frozen-Payload mit bereinigter Bibliotheksumgebung funktionieren. Sprint 4
verpackt anschließend ausschließlich den bereits getesteten Payload.

## 11. Referenzen

- AppImage AppDir:
  <https://docs.appimage.org/reference/appdir.html>
- AppImage manuelle Verpackung:
  <https://docs.appimage.org/packaging-guide/manual.html>
- AppImage FUSE:
  <https://docs.appimage.org/user-guide/troubleshooting/fuse.html>
- PyInstaller Spec-Dateien:
  <https://pyinstaller.org/en/stable/spec-files.html>
- PyInstaller und externe Programme:
  <https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html>
- PyInstaller Linux-Kompatibilität:
  <https://pyinstaller.org/en/stable/usage.html>
- Qt-X11-Anforderungen:
  <https://doc.qt.io/qt-6/linux-requirements.html>

## 12. Umsetzungsnachweis

Die Sprints 0 bis 6 wurden am 27.07.2026 technisch umgesetzt. Erzeugtes
Releaseartefakt:

`dist-appimage/Toolbox-0.42-beta-x86_64.AppImage`

Automatisierte Abschlussprüfung:

- 211 Pytest-Tests bestanden;
- AppDir-Smoke-Test bestanden;
- normaler AppImage-Smoke-Test bestanden;
- AppImage-`--appimage-extract-and-run`-Smoke-Test bestanden;
- AppImage-Argumentweitergabe in allen Startvarianten bestanden;
- Relokation als umbenannte Datei, in einem Pfad mit Leerzeichen, per Symlink und
  aus einem schreibgeschützten Ordner bestanden;
- realer Cinnamon/X11-Test für WM-Klasse, Fenstertitel, Icon-Metadaten,
  Verschieben/Skalieren, reguläres Schließen und XDG-Persistenz bestanden;
- HiDPI-Startpfad mit `QT_SCALE_FACTOR=2` bestanden;
- ELF-Abhängigkeitsprüfung ohne unaufgelöste Bibliotheken bestanden;
- Mint-Basissystembibliotheken und glibc werden nicht mitgebündelt;
- Desktop-Datei ohne Fehler validiert;
- AppStream-Metadaten offline erfolgreich validiert;
- SHA-256-Prüfsumme erfolgreich gegengeprüft;
- zwei Builds mit identischen Eingaben sind bit-identisch;
- Python-, PyInstaller-, AppImage-Runtime-, ICU-, GPL-/LGPL- und Projekthinweise
  sind im AppImage enthalten.

Die manuelle Abnahmecheckliste bleibt bewusst separat und ungekreuzt. Sie erfordert
eine sichtbare Cinnamon/X11-Sitzung und reale Benutzerinteraktion; die entsprechenden
Startpfade und Kernfunktionen sind zusätzlich durch automatisierte Tests abgedeckt.

## 13. Ergebnis des Nachaudits

Der Soll-Ist-Abgleich fand und behob folgende Abweichungen:

1. Linux-`wait` blockierte den GUI-Thread; der Kindprozess wird nun von einem
   Hintergrund-Waiter abgeholt.
2. Gespeicherte Windows-Administrator- und Fensterstatuswerte konnten unter Linux
   noch einen Fehler auslösen oder angezeigt werden; sie werden nun ignoriert
   beziehungsweise ausgeblendet.
3. Ein Help-Text enthielt noch `ffmpeg.exe`; der Text ist nun plattformneutral.
4. Die AppImage-Abnahme prüfte weder Relokation noch echte Argumentweitergabe,
   HiDPI, XCB oder native Fenstereigenschaften; alle Pfade sind jetzt automatisiert.
5. AppDir-Schreibfreiheit und extrahierter AppImage-Inhalt wurden nicht verglichen;
   Inhalts- und Vorher/Nachher-Prüfungen sind ergänzt.
6. Die SHA-256-Datei enthielt einen absoluten Pfad; sie verwendet nun einen
   portablen relativen Dateinamen.
7. `appimagetool` war nicht als Buildinput verifiziert; ein fester SHA-256-Pin und
   ein Preflight-Check sind ergänzt.
8. PyInstaller-Warnungen waren nicht klassifiziert; ein Allowlist-Gate bricht bei
   neuen, ungeprüften Modulwarnungen ab.
9. Der Builder kopierte zahlreiche Mint-Systembibliotheken; diese werden nun
   ausgeschlossen und gegen das zugesicherte Mint-22.3-Basissystem aufgelöst.
10. AppImage-Runtime- und ICU-Lizenztexte fehlten; beide sind jetzt enthalten.
11. Wiederholungsbuilds waren zunächst nicht bit-identisch. Fester Python-Hashseed,
    normalisierte SquashFS-Zeitstempel und serielle SquashFS-Erzeugung machen zwei
    Builds mit identischen Eingaben bit-identisch.
12. Eine einmalige Migrationsstrategie für alte dynamische Konfigurationsordner
    fehlte; die sichere manuelle Strategie ist im README dokumentiert.
13. Ausführbare `.desktop`-Verknüpfungen wurden fälschlich direkt an den Kernel
    übergeben und endeten mit `Exec format error`; normale Linux-Anwendungen
    werden nun standardskonform geparst, ohne Shell gestartet und auf schnelle
    Prozessfehler überwacht. Terminal- und D-Bus-Sonderfälle bleiben ein klar
    gekennzeichneter GIO-Fallback.
14. Desktop-Icons wurden als generische Dateityp-Icons dargestellt; `Icon=` wird
    nun über absolute Dateien oder das aktive XDG-/Cinnamon-Theme aufgelöst.
15. Dateien und URLs konnten nicht auf vorhandene Kacheln gezogen werden;
    `%f`, `%F`, `%u` und `%U` werden nun direkt auf Kachel-Drops angewendet.

Noch als Release-Operator-Prüfung offen bleiben ausschließlich Punkte, die keine
weitere Codeimplementierung darstellen:

- echter Doppelklick im Cinnamon-Dateimanager und subjektive Sichtprüfung des
  Panel-/Dateimanager-Symbols;
- subjektive visuelle HiDPI-Abnahme;
- System-FFmpeg-End-to-End-Test auf einem Zielsystem mit installiertem FFmpeg
  (auf dem Referenzsystem ist FFmpeg derzeit nicht installiert);
- optionaler Wayland-Test.

Finales Artefakt nach dem Nachaudit:

`dist-appimage/Toolbox-0.42-beta-x86_64.AppImage`

- Größe: 60.773.568 Bytes
- SHA-256:
  `cb426ecc10f41c6dba08f9081461bda3f4c61dece5c1e546c6a929ce4a9df45d`

Die Prüfsumme wird vom Buildskript zusätzlich in der portablen
`.sha256`-Begleitdatei erzeugt.
