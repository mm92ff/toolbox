# Umsetzungs- und Release-Validierung

Stand: 8. August 2026
Geprüfter Git-HEAD vor einem Abschluss-Commit: `e7c3e3aa21eecf8223395711578e21b18cb861b8`

## Ergebnis

Die technischen Aufgaben der Sprints 0 bis 7 und die automatisierbaren Aufgaben aus Sprint 8
sind umgesetzt. Beim abschließenden Soll-Ist-Abgleich wurden noch mehrere Lücken gefunden und
geschlossen:

1. Der Ordnerzähler verwendet nun einen einzigen, fensterweiten `FolderCountService`. Damit gilt
   das Limit von zwei Dateisystemjobs auch bei vielen Tabs global und nicht nur je Canvas.
2. Linux- und Windows-Code-Backups schließen `.bin` und `thirdparty` aus und prüfen die neuen
   Pflichtdateien beim Probe-Restore.
3. Der AppImage-Test startet zusätzlich eine normale Toolbox-Instanz und führt währenddessen einen
   isolierten Smoke-Test aus.
4. AppImage-Icons werden mit einem begrenzten Hintergrunddienst statisch aus `.DirIcon` gelesen,
   als PNG normalisiert und gecacht. Das AppImage selbst wird dabei nicht ausgeführt.
5. Die Schriftgröße der Kacheltitel kann wahlweise automatisch aus der Icon-Größe abgeleitet oder
   manuell von 8 bis 24 Pixel eingestellt werden. Vorschau, Kachelgeometrie, QSettings und
   JSON-Import/-Export verwenden dieselbe Einstellung; ältere Profile bleiben im Automatikmodus.
6. Tray-Icon-Sichtbarkeit und Minimieren beim Schließen sind getrennt konfigurierbar. Das Icon ist
   für bestehende Profile standardmäßig sichtbar, wird auf 64 Pixel normalisiert und das dedizierte
   `one_tray.png` ist als verpflichtender Bestandteil des AppImage abgesichert.

Zusätzlich wurden fehlende Fehlerpfadtests für Berechtigungsfehler und Symlink-Schleifen ergänzt.

## Sprintstatus

| Sprint | Status | Nachweis |
|---|---|---|
| 0 – Baseline/Testharness | umgesetzt | zentrales `tests/conftest.py`, externe Netzwerkzugriffe gesperrt, gemeinsame Qt-App |
| 1 – sichere Icons | umgesetzt | keine Ausführung der Zieldatei, deklarative/Sidecar-Auflösung, Cache- und Sicherheitstests |
| 2 – Hintergrundarbeit | umgesetzt | global begrenzter Ordnerdienst, einzelner Größenworker, Abbruch/Generationen/Timeouts |
| 3 – Tray/Einzelinstanz | umgesetzt | ein Close-Pfad, Force-Quit, eindeutige IPC-Resultate und stale-socket-Tests |
| 4 – Einstellungen/Zuordnungen | umgesetzt | zentrales Schema, QSettings-/JSON-Roundtrips, bereinigte Prozessumgebung |
| 5 – Ordner-Browse | umgesetzt | stabile IDs, read-only-Aktionen, gemeinsame sichtbare Entries, differenzierte Fehler |
| 6 – FFmpeg/AppImage | umgesetzt | gepinnte Binär- und Archivhashes, sichere Extraktion, XDG-Ziel, Offline-Build |
| 7 – Repositoryhygiene | umgesetzt | Root-Experimente entfernt, Metadaten/Shell/Ruff/Backup geprüft |
| 8 – automatisierte Abnahme | umgesetzt | AppDir, AppImage, X11, Portabilität, aktive Normalinstanz, Reproduzierbarkeit |
| 8 – manuelle Testmatrix | ausstehend | erfordert bewusste Bedienprüfung durch einen Benutzer vor Veröffentlichung |

## Geprüfte Umgebung

- Linux Mint 22.3 „Zena“, X11
- Python 3.12.13
- PySide6 6.11.1
- pytest 8.4.2
- PyInstaller 6.21.0
- Ruff 0.16.2

## Automatisierte Nachweise

Folgende Prüfungen waren erfolgreich:

```text
env -u LD_LIBRARY_PATH QT_QPA_PLATFORM=offscreen ./.venv/bin/python -m pytest -q
311 passed

env -u LD_LIBRARY_PATH ./.venv/bin/python -m compileall -q app main.py tests
./.venv/bin/ruff check app main.py tests
git diff --check
desktop-file-validate packaging/linux/toolbox.desktop
appstreamcli validate --no-net packaging/linux/io.github.toolbox.Toolbox.appdata.xml
bash -n scripts/*.sh packaging/linux/AppRun
./scripts/create_code_backup.sh --self-test
./scripts/verify-linux-release.sh ./dist-appimage/Toolbox-0.42-beta-x86_64.AppImage
```

Die AppImage-Prüfung deckt normale Ausführung, `--appimage-extract-and-run`, HiDPI, einen
umbenannten Dateinamen, Pfade mit Leerzeichen, Symlinks, ein schreibgeschütztes Verzeichnis, X11
und den Smoke-Test bei parallel laufender Normalinstanz ab.

Zwei vollständige Builds mit denselben Eingaben erzeugten denselben SHA-256-Wert:

```text
a5535f1f9020c72c1500b9506256187c9be9a3bb17dcb757abc15d102eeb184f
```

Finales Artefakt:

```text
dist-appimage/Toolbox-0.42-beta-x86_64.AppImage
Größe: 120960192 Byte
```

## Noch erforderliche manuelle Freigabe

Vor einer Veröffentlichung müssen die in Sprint 8 beschriebenen Bedienfälle noch manuell
abgehakt werden. Dazu gehören insbesondere echtes Drag-and-drop verschiedener Desktopdateien,
Tray-Bedienung, VLC/Flatpak-Dateizuordnungen, Profil-Export/-Import und Video-Vorschau auf einem
Rechner ohne System-FFmpeg. Automatisierte Tests reduzieren das Risiko, ersetzen diese bewusste
Endanwenderprüfung aber nicht.

Die im Plan empfohlene Commit-Aufteilung wurde bei diesem Audit nicht nachträglich erzeugt. Der
Arbeitsstand bleibt bis zu einem ausdrücklich gewünschten Abschluss-Commit nachvollziehbar im
Working Tree erhalten.
